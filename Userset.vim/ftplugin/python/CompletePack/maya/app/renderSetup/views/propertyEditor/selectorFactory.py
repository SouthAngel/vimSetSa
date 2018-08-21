"""Property editor selector factory.

   Each collection object has a selector that is responsible for determining
   objects that:

   o are members of the render layer, and
   o will be overridden.

   The property editor supports different UIs for different selector
   types.  The property editor selector factory provides an extensible
   mechanism to create the UI for various selector types.

   To create a property editor UI for a selector class, a creator callable
   is registered on the data model selector class type.  On creation, the
   creator callable is given the data model selector object.

   The return value of the creator is a builder object for the selector
   property UI.  This object must have a build() method, whose argument is
   the property editor UI layout for the selector.

   The selector factory is a singleton."""
import maya
maya.utils.loadStringResourcesForModule(__name__)


kAlreadyRegistered = maya.stringTable['y_selectorFactory.kAlreadyRegistered' ]

# Dictionary of creators.  Key is data model type name, value is a creator
# callable.
_creators = {}

def register(typeName, creator):
    """Register a property editor UI creator for selector data model type.

    Raises a RuntimeError if a creator had already been registered."""

    # The following should be an assertion.
    if typeName in _creators:
        raise RuntimeError(kAlreadyRegistered % typeName)

    _creators[typeName] = creator


def unregister(typeName):
    """Unregister a property editor UI creator for selector data model type.

    Raises a KeyError if a creator had not already been registered."""

    del _creators[typeName]

def create(selector):
    """Create a property editor UI for selector.

    The argument is the data model selector object

    The return object is the selector property UI builder.

    Raises a KeyError if a creator had not already been registered."""

    return _creators[selector.kTypeName](selector)

def selectorTypes():
    return _creators.keys()

def entry(typeName):
    """Return the creator for the argument selector data model type."""

    return _creators[typeName]
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
