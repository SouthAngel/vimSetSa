"""cursor guard support for wait cursor handling.

   This module provides a context manager to have a convenient
   wait cursor guard mechanism.  It ensures that the wait cursor is started
   and stopped at expected time.
"""

from PySide2.QtCore import Qt
from PySide2.QtWidgets import QApplication

class WaitCursorMgr(object):
    """ Safe way to manage wait cursors

    Example:
        with WaitCursorMgr():
            doSomeHeavyOperation()
    """
    def __enter__(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)

    def __exit__(self, type, value, traceback):
        QApplication.restoreOverrideCursor()


def waitCursor():
    """ wait cursor decorator to manage the cursor scope

    Example:
        @waitCursor()
        def doSomeHeavyOperation():
    """

    def decorator(f):
        def wrapper(*args, **kwargs):
            with WaitCursorMgr():
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
