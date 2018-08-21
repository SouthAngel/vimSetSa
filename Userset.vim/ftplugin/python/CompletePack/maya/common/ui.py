"""
Maya-specific utility tools (classes and method) for UI

These are utilities to interact with Maya UI.  They give basic building blocks
to wrap simple operations in easier-to-use tools.

These can be used inside Maya and MayaLT.
"""
import maya
maya.utils.loadStringResourcesForModule(__name__)


import maya.cmds as cmds


__all__ = [
    'LayoutManager',
    'showMessageBox',
    'showConfirmationDialog',
    ]


class LayoutManager(object):
    """
    This class is a simple manager that is responsible for returning to the
    parent layout when exiting.

    It should be used when layering several layouts to make it easier to track
    which layout is currently being populated.  It makes code easier to read by
    grouping all UI creation under a given layout within the same indentation
    level.
    """

    def __init__(self, name):
        """
        Simple constructor that just remembers the name of the given layout.
        """
        self.name = name

    def __enter__(self):
        """
        When entering the ``with`` statement, this object returns the
        handled layout.
        """
        return self.name

    def __exit__(self, type, value, traceback):
        cmds.setParent('..')


def showMessageBox(title, message, icon=None):
    """
    This method pops up a Maya message box with the given title and the given
    message.

    It also accepts an optional icon parameter which can receive the same
    values as the confirmDialog command does.
    """

    extraParams = {}
    if icon:
        extraParams['icon'] = icon

    okButtonString = maya.stringTable['y_ui.kOK' ]
    cmds.confirmDialog(
        title=title,
        message=message,
        button=okButtonString,
        defaultButton=okButtonString,
        **extraParams
        )


def showConfirmationDialog(title, message):
    """
    This method pops up a Maya confirmation dialog with the given title and the
    given message.

    It returns True if the user accepted, False otherwise.
    """

    okButtonString = maya.stringTable['y_ui.kOKButton' ]
    cancelButtonString = maya.stringTable['y_ui.kCancelButton' ]
    answer = cmds.confirmDialog(
        title=title,
        message=message,
        button=[okButtonString, cancelButtonString],
        defaultButton=okButtonString,
        icon='question'
        )

    return answer == okButtonString
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
