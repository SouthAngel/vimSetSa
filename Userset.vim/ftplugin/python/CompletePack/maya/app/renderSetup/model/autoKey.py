"""Auto keyframe support.

This module encapsulates functions to use the autoKeyframe command to
support auto keying of overrides.

If an overridden attribute is written to, and it is overridden by a value
override, the apply override chain is traversed, and the appropriate
override attribute is written to (see the applyOverride module
documentation for details).

If this override attribute satisfies the autoKeyframe requirements, which
include among others:

- Have at least one keyframe set
- Support the keyable property (see plug.Plug.isKeyable documentation for
  semantics)

Then the override attribute will be keyframed.

Using the autoKeyframe command has the following desirable properties:

- The autoKeyframe code fully encapsulates what attributes are interesting
  to auto key.
- The autoKeyframe code correctly handles undo / redo so that any key
  frame addition is undone atomically with the corresponding set value command.
"""

import maya.app.renderSetup.model.plug as plug

import maya.cmds as cmds

def autoKeyed():
    """Returns the attribute(s) that the autoKeyframe command will set.

    The attribute(s) is returned in a set.  If autoKeyframe is off, an
    empty set is returned."""
    
    # If autoKeyframe is off, nothing to do.
    if not isEnabled():
        return set()

    autoKeyed = cmds.autoKeyframe(query=True, listAttr=True)
    return set() if autoKeyed is None else set(autoKeyed)

def isEnabled():
    return cmds.autoKeyframe(query=True, state=True)


def setValue(mPlug, value, autoKey):
    """Set the argument value on the argument plug, setting an
    autoKeyframe on that attribute, if autoKey is True.

    The plug argument must be an MPlug."""

    if autoKey:
        cmds.autoKeyframe(edit=True, addAttr=mPlug.name())

    plug.Plug(mPlug).value = value
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
