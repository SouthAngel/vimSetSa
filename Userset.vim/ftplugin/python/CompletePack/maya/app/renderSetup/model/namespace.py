"""Render setup model namespace guard.
   
   This module implements a context and an associated decorator to run 
   code with the root or a given Maya namespace as current.
   It must decorate every function that involves render setup
   nodes creation and renaming.
"""

from maya import cmds

ROOT_NAMESPACE = ':'

class NamespaceGuard:
    """ Safe way to set namespace using the 'with' statement.
    It will set the namespace back to the previously used namespace on exit from the block.
    The namespace changes WILL affect undo stack. Make sure to wrap it in an 
    undo chunk if needed.
    
    Example:
        with NamespaceGuard(ROOT_NAMESPACE):
            someCreateNodeFunction()
    """

    def __init__(self, namespace):
        self.namespace = namespace
        self.previous  = None
        self.isSame    = None

    def __enter__(self):
        self.previous = cmds.namespaceInfo(absoluteName=True)
        # Within file I/O, calling the namespace command is prohibited.
        # Our use of namespace guards causes them to be invoked, but
        # without changing the namespace itself.  Therefore, avoid calling
        # the namespace command when no change is needed.
        self.isSame = self.previous == self.namespace
        if not self.isSame:
            cmds.namespace(set=self.namespace)
        return None

    def __exit__(self, type, value, traceback):
        if not self.isSame:
            cmds.namespace(set=self.previous)

def guard(name):
    def decorator(f):
        def wrapper(*args, **kwargs):
            with NamespaceGuard(name):
                return f(*args, **kwargs)
        return wrapper
    return decorator

root = guard(ROOT_NAMESPACE)

def RootNamespaceGuard():
    return NamespaceGuard(ROOT_NAMESPACE)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
