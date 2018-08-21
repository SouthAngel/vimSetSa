import maya

maya.stringTable['y_fileLoadMonitor.kErrorSwitchToRenderLayer'] = u'This file contains legacy render layers and Maya is currently in Render Setup mode. This combination is unsupported.  You can switch to Legacy Render Layers mode from the Preferred Render Setup system drop-down list in the Rendering section of the Preferences window.'
maya.stringTable['y_fileLoadMonitor.kErrorCombiningNewToLegacy'] = u'You are attempting to load a file that contains render setup nodes into a scene that uses legacy render layers. This combination is unsupported and may result in unexpected behavior.'
maya.stringTable['y_fileLoadMonitor.kErrorSwitchToRenderSetup'] = u'This file contains render setup nodes and Maya is currently in Legacy Render Layers mode. This combination is unsupported. You can switch to Render Setup mode from the Preferred Render Setup system drop-down list in the Rendering section of the Preferences window.'
maya.stringTable['y_fileLoadMonitor.kWarningInactiveRenderSetup'] = u'This file contains render setup nodes. Render setup nodes from an imported or referenced file cannot be modified. It is recommended that you first save the file with the master layer set as visible before it is imported or referenced.'
maya.stringTable['y_fileLoadMonitor.kErrorCombiningLegacyToNew'] = u'You are attempting to load a file that contains legacy render layers into a scene that uses render setup. This combination is unsupported and may result in unexpected behavior.'

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
