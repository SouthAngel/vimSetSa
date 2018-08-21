import maya
maya.utils.loadStringResourcesForModule(__name__)

import maya.cmds as cmd
import adskPrepareRender

# Set up the adskPrepareRender custom traversal set, but don't make it
# the default traversal set, since doing so actually changes the scene,
# as it changes the corresponding render global attribute.

cmd.prepareRender(edit=True, traversalSet='adskPrepareRender',
                  preRender=adskPrepareRender.preRender)
cmd.prepareRender(edit=True, traversalSet='adskPrepareRender',
                  saveAssemblyConfig=True)
cmd.prepareRender(edit=True, traversalSet='adskPrepareRender',
                  label=maya.stringTable['y___init__.kTraversalSetLabel' ])
cmd.prepareRender(edit=True, traversalSet='adskPrepareRender',
                  settingsUI=adskPrepareRender.settingsUI)
cmd.prepareRender(edit=True, traversalSet='adskPrepareRender',
                  traversalSetInit=adskPrepareRender.createPrepareRenderGlobalsNode)

# As of 2-Dec-2012, the default traversal set will be "null", and thus
# assembly nodes will be rendered with their acive representation.
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
