import maya
maya.utils.loadStringResourcesForModule(__name__)

from PySide2.QtGui import *
from PySide2.QtWidgets import *
from PySide2.QtCore import *

import maya.cmds as cmds
import os

def doNotShowChanged():
    # Toggle the option var
    showDialog = cmds.optionVar(q="showMentalRayNotAvailableDialog")
    cmds.optionVar(iv=("showMentalRayNotAvailableDialog", int(not showDialog)))

def show():
    # Early out if we're in batch mode or are running the tests
    if cmds.about(batch=True) or ('MAYA_RUNNING_TESTS' in os.environ and os.environ['MAYA_RUNNING_TESTS'] == '1'):
        return

    # Create our option var if it doesn't exist
    if not cmds.optionVar(exists="showMentalRayNotAvailableDialog"):
        cmds.optionVar(iv=("showMentalRayNotAvailableDialog", 1))

    # Show the dialog if the option var is set to 1
    if cmds.optionVar(q="showMentalRayNotAvailableDialog"):
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setTextFormat(Qt.RichText)
        msgBox.setWindowTitle(maya.stringTable['y_mentalRayNotAvailableDialog.kWindowTitle' ])
        msgBox.setText(maya.stringTable['y_mentalRayNotAvailableDialog.kText' ])
        msgBox.setInformativeText(maya.stringTable['y_mentalRayNotAvailableDialog.kInformativeText' ])
        msgBox.setStandardButtons(QMessageBox.Ok)
        msgBox.setDefaultButton(QMessageBox.Ok)
        cb = QCheckBox(maya.stringTable['y_mentalRayNotAvailableDialog.kCheckBoxText' ])
        msgBox.setCheckBox(cb)
        cb.stateChanged.connect(doNotShowChanged)
        
        msgBox.exec_()
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
