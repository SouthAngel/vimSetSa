"""Render setup model undo support.

   This module provides a context manager that provides for convenient undo
   macro commands (called "chunks" in Maya terminology).  It ensures that
   only the top-level call to the undo context manager will open and close
   a chunk, thus providing a single, named entry on the undo stack."""

import maya.api.OpenMaya as OpenMaya

from maya import cmds

class CtxMgr:
    """Safe way to manage group undo chunks using the 'with' command.
    It will close the chunk automatically on exit from the block
    
    Example:
        with CtxMgr('Create Poly Cubes'):
            cmds.polyCube()
            cmds.polyCube()
        cmds.undo() # Will undo both polyCube() creation calls."""

    # Shamelessly adapted from apiMPxComponentShapeTest.py.

    openChunk = True
    
    def __init__(self, name='unnamedOperation'):
        self.name = name
        self.closeChunk = False

    def __enter__(self):
        if CtxMgr.openChunk:
            self.closeChunk = True
            CtxMgr.openChunk = False
            cmds.undoInfo(openChunk=True, chunkName=self.name)
        return None

    def __exit__(self, type, value, traceback):
        if self.closeChunk:
            cmds.undoInfo(closeChunk=True)
            CtxMgr.openChunk = True

def chunk(chunkName):
    """Undo decorator to name and group in a single chunk all commands
    inside the decorated callable."""

    # Decorator functions always take a single argument (usually the
    # decorated function), so we need to use a layered approach so we can
    # also pass in the undo chunk name.
    #
    # The top-level decorator function ("chunk") is only there to pass in
    # the undo chunk name as its single argument.  It returns the actual
    # decorator function ("decorator").  decorator is the function doing
    # the decorating: its single argument is the decorated function, and it
    # returns the wrapper ("wrapper") function, which is used instead of
    # the decorated function.  Where the decorated function would have been
    # called, wrapper is now called instead, and it uses the CtxMgr context
    # to group all undoable commands into a single, named undo chunk.

    def decorator(f):
        def wrapper(*args, **kwargs):
            with CtxMgr(chunkName):
                return f(*args, **kwargs)
        return wrapper
    return decorator

class SuspendUndo:
    """Safe way to suspend and resume undo logging using the 'with' command.
    It will automatically resume undo on exit from the block
    
    Example:
        with SuspendUndo():
            cmds.polyCube()
            cmds.polyCube()
        cmds.undo() # Will not undo the creation calls."""

    # Shamelessly adapted from above.
    
    def __init__(self):
        self.previouslySuspended = False

    def __enter__(self):
        self.previouslySuspended = not cmds.undoInfo(query=True, state=True)
        if not self.previouslySuspended:
            cmds.undoInfo(stateWithoutFlush=False)
        return None

    def __exit__(self, type, value, traceback):
        if not self.previouslySuspended:
            cmds.undoInfo(stateWithoutFlush=True)

def suspend():
    """Undo decorator to suspend and resume undo for all commands
    inside the decorated callable."""

    def decorator(f):
        def wrapper(*args, **kwargs):
            with SuspendUndo():
                return f(*args, **kwargs)
        return wrapper
    return decorator

#==============================================================================
# CLASS NotifyPostRedoCmd
#==============================================================================

class NotifyPostRedoCmd(OpenMaya.MPxCommand):
    """Helper command notify after redo.

    This command is a private implementation detail of this module and should
    not be called otherwise."""

    kCmdName = 'notifyPostRedo'

    # Command data.  Must be set before creating an instance of the command
    # and executing it.
    callable = None

    def isUndoable(self):
        return True

    def doIt(self, args):
        # Completely ignore the MArgList argument, as it's unnecessary:
        # arguments to the commands are passed in Python object form
        # directly to the command's constructor.

        if self.callable is None:
            cmds.warning(kCmdPrivate % self.kCmdName)
        else:
            self.redoIt()

    @staticmethod
    def execute(callable):
        NotifyPostRedoCmd.callable = callable
        cmds.notifyPostRedo()
        NotifyPostRedoCmd.callable = None

    @staticmethod
    def creator():
        return NotifyPostRedoCmd(NotifyPostRedoCmd.callable)

    def __init__(self, callable):
        super(NotifyPostRedoCmd, self).__init__()
        self.callable = callable

    def redoIt(self):
        self.callable()

    def undoIt(self):
        pass

#==============================================================================
# CLASS NotifyPostUndoCmd
#==============================================================================

class NotifyPostUndoCmd(OpenMaya.MPxCommand):
    """Helper command notify after undo.

    This command is a private implementation detail of this module and should
    not be called otherwise."""

    kCmdName = 'notifyPostUndo'

    # Command data.  Must be set before creating an instance of the command
    # and executing it.
    callable = None

    def isUndoable(self):
        return True

    def doIt(self, args):
        # Completely ignore the MArgList argument, as it's unnecessary:
        # arguments to the commands are passed in Python object form
        # directly to the command's constructor.

        if self.callable is None:
            cmds.warning(kCmdPrivate % self.kCmdName)
        else:
            self.redoIt()

    @staticmethod
    def execute(callable):
        NotifyPostUndoCmd.callable = callable
        cmds.notifyPostUndo()
        NotifyPostUndoCmd.callable = None

    @staticmethod
    def creator():
        return NotifyPostUndoCmd(NotifyPostUndoCmd.callable)

    def __init__(self, callable):
        super(NotifyPostUndoCmd, self).__init__()
        self.callable = callable

    def redoIt(self):
        pass

    def undoIt(self):
        self.callable()

class NotifyCtxMgr:
    """Safe way to manage group undo chunks using the 'with' command.

    It will close the chunk automatically on exit from the block.
    Supports post undo and post redo notification callables.
    
    Example:
        with NotifyCtxMgr('Create Poly Cubes', postRedo, postUndo):
            cmds.polyCube()
            cmds.polyCube()
        # Will undo both polyCube() creation calls, and call postUndo.
        cmds.undo()

    If a single callable is given, it will be called post undo and post redo."""
    
    def __init__(self, name, postRedo, postUndo=None):
        self.name = name
        self.openChunk = True
        self.closeChunk = False
        self.postRedo = postRedo
        self.postUndo = postUndo if postUndo else postRedo

    def __enter__(self):
        if self.openChunk:
            self.closeChunk = True
            self.openChunk = False
            cmds.undoInfo(openChunk=True, chunkName=self.name)
            # On undo, this is run last.
            NotifyPostUndoCmd.execute(self.postUndo)
        return None

    def __exit__(self, type, value, traceback):
        if self.closeChunk:
            # On redo, this is run last.
            NotifyPostRedoCmd.execute(self.postRedo)
            cmds.undoInfo(closeChunk=True)
            NotifyCtxMgr.openChunk = True

def notify(chunkName, postRedo, postUndo=None):
    """Undo decorator to name and group in a single chunk all commands
    inside the decorated callable.

    The postRedo and postUndo callables are called at end of redo (and do),
    and at end of undo, respectively.  If a single callable is given, it
    will be called both at end of redo and at end of undo."""

    # See chunk() comments.
    def decorator(f):
        def wrapper(*args, **kwargs):
            with NotifyCtxMgr(chunkName, postRedo, postUndo):
                return f(*args, **kwargs)
        return wrapper
    return decorator
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
