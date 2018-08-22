from PySide2.QtWidgets import QAction

from contextlib import contextmanager
import sys


@contextmanager
def excepthookGuard(consumer):
    try:
        consumer.exceptionRaised = None
        # Someone could have changed the default hook
        currentHook = sys.excepthook
        # Replace the current hook by the Action one
        sys.excepthook = consumer.excepthook

        yield

    finally:
        sys.excepthook = currentHook
        # Rethrow the exception if one was trapped
        if consumer.exceptionRaised is not None:
            raise consumer.exceptionRaised 


class Action(QAction):

    exceptionRaised = None

    def excepthook(self, type, value, traceback):
        # As per
        #
        # http://pytest-qt.readthedocs.org/en/latest/virtual_methods.html
        #
        # PySide (and PyQt) prevent Python exceptions from escaping out of
        # Qt virtual function calls (like trigger()).  Therefore, install
        # an exception hook so we can record an exception was raised.
        sys.__excepthook__(type, value, traceback)    

        # Keep the thrown exception to rethrow it in __exit__ of the context manager 
        self.exceptionRaised = value

    def trigger(self):
        """ The only method Render Setup is currently using from the QAction interface """
        with excepthookGuard(self):
            super(Action, self).trigger()
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
