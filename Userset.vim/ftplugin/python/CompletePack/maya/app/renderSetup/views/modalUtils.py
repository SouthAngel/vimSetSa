import maya.OpenMayaUI as OpenMayaUI

from PySide2.QtCore import QFileInfo, QTimer
from PySide2.QtWidgets import QFileDialog
from shiboken2 import wrapInstance

from functools import partial

def acceptFileDialog(fileName, interval=200):
    """Set up a timer-based event to accept a file dialog with the argument
    file name.

    The timer interval is optionally specified in milliseconds."""

    QTimer.singleShot(
        interval, partial(_fileDialogTimerExpired, fileName))

def _findFileDialog():
    # Find the file dialog singleton.

    # QApplication.topLevelWidgets() returns a list, with one of the
    # widgets being named 'QFileDialog', but unfortunately the type of this
    # widget is QWidget, and isinstance(widget, QFileDialog) returns
    # false.  Use MQtUtil instead.

    ptr = OpenMayaUI.MQtUtil.findControl('QFileDialog')
    return wrapInstance(long(ptr), QFileDialog)

def _fileDialogTimerExpired(fileName):
    # On expiration of the file dialog timer, set the selected file name onto
    # the dialog, and accept it.

    fileDialog = _findFileDialog()

    # As per
    #
    # http://www.frattv.com/automatically-saving-a-file-with-qfiledialog/
    #
    # QFileDialog source code requires the file dialog to not be visible in
    # order to select a file.

    fileInfo = QFileInfo(fileName)

    fileDialog.setVisible(False)
    fileDialog.setDirectory(fileInfo.dir())
    fileDialog.selectFile(fileInfo.fileName())
    fileDialog.setVisible(True)
    fileDialog.accept()
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
