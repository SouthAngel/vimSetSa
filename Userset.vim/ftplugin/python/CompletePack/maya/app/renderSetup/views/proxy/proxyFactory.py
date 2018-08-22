"""Qt proxy item factory.

   This factory creates Qt proxy items from render setup data model nodes.
   It provides an extensible mechanism to create Qt proxy items for various
   render setup data model types.

   To create a Qt proxy item for a data model class, a creator callable is
   registered on the data model class type.  On creation, the creator
   callable is given the data model node.  It must return an instance of a
   class derived from ModelProxyItem.

   The proxy factory is a singleton."""
import maya
maya.utils.loadStringResourcesForModule(__name__)


kAlreadyRegistered = maya.stringTable['y_proxyFactory.kAlreadyRegistered' ]

# Dictionary of creators.  Key is data model type name, value is a creator
# callable with node argument.
_creators = {}

def register(typeName, creator):
    """Register a Qt proxy item creator for data model type.

    Raises a RuntimeError if a creator had already been registered."""

    # The following should be an assertion.
    if typeName in _creators:
        raise RuntimeError(kAlreadyRegistered % typeName)

    _creators[typeName] = creator


def unregister(typeName):
    """Unregister a Qt proxy item creator for data model type.

    Raises a KeyError if a creator had not already been registered."""

    del _creators[typeName]

def create(node):
    """Create a Qt proxy item for data model node.

    Raises a KeyError if a creator had not already been registered."""

    return _creators[node.kTypeName](node)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
