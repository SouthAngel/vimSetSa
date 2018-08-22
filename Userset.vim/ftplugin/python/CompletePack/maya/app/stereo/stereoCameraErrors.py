import maya
maya.utils.loadStringResourcesForModule(__name__)

import maya.cmds as cmds
import maya.mel as mel
import sys

"""
This module provides a wrapper around error messages and warnings that
can be reported to the user.
"""

# Internal method to get a message from the stringId
def __getMessage(strId, arg1, arg2):
	return maya.stringTable['y_stereoCameraErrors.' + strId] % \
		   {'arg1': arg1, 'arg2': arg2}

# Display a warning defined by a stringId.
def displayWarning( strId, arg1=None, arg2=None ):
	cmds.warning(__getMessage(strId, arg1, arg2))

# Display an error defined by a stringId.
def displayError( strId, arg1=None, arg2=None ):
	try:
		msg = __getMessage(strId, arg1, arg2)
		msg = msg.replace('"', '\\"')
		mel.eval('error "%s";' % msg)
	except:
		pass

# This table contains the centralized error messages.
gMsgTable = [
	maya.stringTable['y_stereoCameraErrors.kRigCommandPython' ],
	maya.stringTable['y_stereoCameraErrors.kRigCommandNotFound' ],
	maya.stringTable['y_stereoCameraErrors.kRigCommandFailed' ],
	maya.stringTable['y_stereoCameraErrors.kNotACamera' ],
	maya.stringTable['y_stereoCameraErrors.kRigCommandBadParent' ],
	maya.stringTable['y_stereoCameraErrors.kRigCommandInstance' ],
	maya.stringTable['y_stereoCameraErrors.kRigToolNoName' ],
	maya.stringTable['y_stereoCameraErrors.kRigToolMultiByteName' ],
	maya.stringTable['y_stereoCameraErrors.kRigToolNoCreate' ],
	maya.stringTable['y_stereoCameraErrors.kRigToolAlreadyExists' ],

	maya.stringTable['y_stereoCameraErrors.kMissingPythonCB' ],
	maya.stringTable['y_stereoCameraErrors.kLanguageNotSupported' ],
	maya.stringTable['y_stereoCameraErrors.kAttributeNotFound' ],
	maya.stringTable['y_stereoCameraErrors.kAttributeAlreadyExists' ],
	maya.stringTable['y_stereoCameraErrors.kCannotConnect' ],

	maya.stringTable['y_stereoCameraErrors.kInvalidCommandSpecified' ],

	maya.stringTable['y_stereoCameraErrors.kPluginNotLoaded' ],

	maya.stringTable['y_stereoCameraErrors.kNotAValidStereoCamera' ],

	maya.stringTable['y_stereoCameraErrors.kNoStereoCameraFound' ],

	maya.stringTable['y_stereoCameraErrors.kNothingSelected' ],

	maya.stringTable['y_stereoCameraErrors.kNoValidPanelsFound' ],

	maya.stringTable['y_stereoCameraErrors.kCannotCreateRig' ],

	maya.stringTable['y_stereoCameraErrors.kRigReturnError' ],
	maya.stringTable['y_stereoCameraErrors.kRigReturnNotArray' ],
	maya.stringTable['y_stereoCameraErrors.kNoStereoRigCommand' ],
	maya.stringTable['y_stereoCameraErrors.kNoDataInCameraSet' ],
	maya.stringTable['y_stereoCameraErrors.kNoValidCameraSelected' ],
	maya.stringTable['y_stereoCameraErrors.kNoObjectsSelected' ],
	maya.stringTable['y_stereoCameraErrors.kNoMultibyte' ],
	maya.stringTable['y_stereoCameraErrors.kRigNotFound' ],
	maya.stringTable['y_stereoCameraErrors.kDefaultRigSwap' ]
]
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
