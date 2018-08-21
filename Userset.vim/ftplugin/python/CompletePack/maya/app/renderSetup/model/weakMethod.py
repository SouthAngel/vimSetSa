"""Support weak references to bound methods.

Weak references to bound methods cannot be created directly: if no
strong reference to the bound method is kept, the bound method object is
immediately garbage collected, and the weak reference immediately points to
a dead object and returns None.  See:

http://stackoverflow.com/questions/599430/why-doesnt-the-weakref-work-on-this-bound-method

This module supports the intent, namely a bound method that can only be called
while its object is alive, and keeps its object by weak reference."""

import weakref

class Method(object):
    """Wraps a method such that the bound method's object is held only by
    weak reference."""

    def isAlive(self):
        return self._object() is not None

    def __init__(self, method):
        # im_self returns the instance method self object.
        self._object = weakref.ref(method.im_self)
        # im_func returns the instance method function object.
        self._method = method.im_func

    def __call__(self, *posArgs, **kwArgs):
        return self._method(
            self._object(), *posArgs, **kwArgs) if self.isAlive() else None
    
    # As per recommendations
    # https://docs.python.org/2/reference/datamodel.html#object.__eq__
    # implement both __eq__ and __ne__
    def __eq__(self, other):
        return type(other) is type(self) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self == other

# Convenience function.
def create(method):
    return Method(method)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
