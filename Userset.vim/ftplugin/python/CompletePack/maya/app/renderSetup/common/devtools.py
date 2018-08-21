
def abstractmethod(f):
    '''Decorator for an abstract method. Raise an exception if the function is not overridden by child class.'''
    def wrapper(*args, **kwargs):
        self = args[0]
        import inspect
        raise RuntimeError("Abstract function called from: " + self.__class__.__name__ +"."+ f.__name__ +"("+ str(inspect.getargspec(f))+")")
    return wrapper
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
