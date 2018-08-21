import maya

maya.stringTable['y_stereoCameraErrors.kNotAValidStereoCamera'] = u'The selected object(s) are not a valid stereo camera.'
maya.stringTable['y_stereoCameraErrors.kNoDataInCameraSet'] = u"There is no layer data in the camera set node '%(arg1)s'."
maya.stringTable['y_stereoCameraErrors.kInvalidCommandSpecified'] = u'You have specified an invalid command name. '
maya.stringTable['y_stereoCameraErrors.kRigToolAlreadyExists'] = u"Rig tool '%(arg1)s' already exists."
maya.stringTable['y_stereoCameraErrors.kNoValidPanelsFound'] = u'Unable to find a valid stereo panel to display into. Do you have the StereoCamera plugin loaded?'
maya.stringTable['y_stereoCameraErrors.kRigCommandPython'] = u"Rig '%(arg2)s': Python creation command '%(arg1)s' needs to be in the form 'module.function'."
maya.stringTable['y_stereoCameraErrors.kRigCommandFailed'] = u"Rig '%(arg2)s': creation command '%(arg1)s' failed."
maya.stringTable['y_stereoCameraErrors.kRigToolNoCreate'] = u'Missing rig tool creation procedure.'
maya.stringTable['y_stereoCameraErrors.kRigCommandInstance'] = u'Invalid rig command output: Instancing is allowed inside the rig.'
maya.stringTable['y_stereoCameraErrors.kCannotCreateRig'] = u"Error while trying to create a stereo rig '%(arg1)s'."
maya.stringTable['y_stereoCameraErrors.kRigCommandBadParent'] = u"Invalid rig command output: Camera '%(arg1)s' is not under root '%(arg2)s'."
maya.stringTable['y_stereoCameraErrors.kCannotConnect'] = u'Cannot create and connect attribute %(arg1)s on node %(arg2)s.'
maya.stringTable['y_stereoCameraErrors.kRigReturnNotArray'] = u"Stereo rig creation for '%(arg1)s' did not return an array"
maya.stringTable['y_stereoCameraErrors.kNoStereoRigCommand'] = u"There is no stereo rig definition for '%(arg1)s'. The Custom Stereo Rig Editor can be used to add such a definition."
maya.stringTable['y_stereoCameraErrors.kNoObjectsSelected'] = u'You must select transform objects to make/break links.'
maya.stringTable['y_stereoCameraErrors.kAttributeNotFound'] = u'Invalid rig: attribute %(arg1)s does not exists on node %(arg2)s.'
maya.stringTable['y_stereoCameraErrors.kNothingSelected'] = u'Please select an object to converge on.'
maya.stringTable['y_stereoCameraErrors.kNotACamera'] = u"Invalid rig command output: Object '%(arg1)s' (element %(arg2)d) is not a camera."
maya.stringTable['y_stereoCameraErrors.kLanguageNotSupported'] = u"Unsupported language '%(arg1)s' for custom rig '%(arg2)s'."
maya.stringTable['y_stereoCameraErrors.kDefaultRigSwap'] = u"The default rig has been swapped out with '%(arg1)s'"
maya.stringTable['y_stereoCameraErrors.kPluginNotLoaded'] = u'The plugin has not been loaded. Attempting to load the plug-in.'
maya.stringTable['y_stereoCameraErrors.kRigCommandNotFound'] = u"Rig '%(arg2)s': creation command '%(arg1)s' not found."
maya.stringTable['y_stereoCameraErrors.kRigReturnError'] = u"Stereo rig creation for '%(arg1)s' returned %(arg2)d objects. Expecting 3."
maya.stringTable['y_stereoCameraErrors.kNoStereoCameraFound'] = u"Inconsistant stereo structure: cannot find a connection for attribute '%(arg2)s' on the stereo rig for object '%(arg1)s'."
maya.stringTable['y_stereoCameraErrors.kMissingPythonCB'] = u"Cannot find python function '%(arg1)s' for custom rig '%(arg2)s'."
maya.stringTable['y_stereoCameraErrors.kRigToolNoName'] = u'Missing rig tool name.'
maya.stringTable['y_stereoCameraErrors.kNoValidCameraSelected'] = u'You must select a camera that is attached to a camera set (multi-rig).'
maya.stringTable['y_stereoCameraErrors.kAttributeAlreadyExists'] = u'Attribute %(arg1)s already exists on node %(arg2)s, but is not of message type.'
maya.stringTable['y_stereoCameraErrors.kRigNotFound'] = u"The rig type '%(arg1)s', could not be found in the rig database. The specified multi-rig will not be created."
maya.stringTable['y_stereoCameraErrors.kNoMultibyte'] = u"The multi-byte name, '%(arg1)s', is not permitted for multi-rig creation."
maya.stringTable['y_stereoCameraErrors.kRigToolMultiByteName'] = u"Requested name '%(arg1)s' contains multibyte characters."

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
