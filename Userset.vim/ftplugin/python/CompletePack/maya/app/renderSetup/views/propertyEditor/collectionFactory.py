"""Property editor collection factory.

   The property editor supports different UIs for different collection
   types.  The property editor collection factory provides an extensible
   mechanism to create the UI for various collection types.

   To create a property editor UI for a collection class, a creator
   callable is registered on the data model collection class type.
   On creation, the creator callable is given a weak reference to the
   corresponding proxy item, and the UI parent.  It must return an instance
   of a class derived from MayaQWidgetBaseMixin and QGroupBox.

   The collection factory is a singleton."""
import maya
maya.utils.loadStringResourcesForModule(__name__)


import weakref

kAlreadyRegistered = maya.stringTable['y_collectionFactory.kAlreadyRegistered' ]

# Dictionary of creators.  Key is data model type name, value is a creator
# callable with weak ref to proxy item and UI parent arguments.
_creators = {}

def register(typeName, creator):
    """Register a property editor UI creator for collection type.

    Raises a RuntimeError if a creator had already been registered."""

    # The following should be an assertion.
    if typeName in _creators:
        raise RuntimeError(kAlreadyRegistered % typeName)

    _creators[typeName] = creator


def unregister(typeName):
    """Unregister a property editor UI creator for collection type.

    Raises a KeyError if a creator had not already been registered."""

    del _creators[typeName]

def create(proxyItem, parent):
    """Create a property editor UI for collection type.

    Raises a KeyError if a creator had not already been registered."""

    # Give a weakref of the proxyItem to the creator.
    return _creators[proxyItem.model.kTypeName](weakref.ref(proxyItem), parent)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
