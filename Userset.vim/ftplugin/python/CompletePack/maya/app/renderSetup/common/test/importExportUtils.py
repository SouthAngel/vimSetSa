"""Utilities for render setup import / export testing."""

import maya.app.renderSetup.model.renderSetup as renderSetup

import json

# Cannot name function "import", as this is a reserved Python keyword.
def importFile(filename):
    with open(filename, "r") as file:
        renderSetup.instance().decode(json.load(file), renderSetup.DECODE_AND_OVERWRITE, None)

def exportFile(filename):
    with open(filename, "w+") as file:
        json.dump(renderSetup.instance().encode(None), fp=file, indent=2, sort_keys=True)

def readFile(file):
    """Returns a list of the lines in the argument file."""
    with open(file, 'r') as f:
        data = f.read().split('\n')
        # Strip data of any windows newline character
        data = [d.rstrip('\r') for d in data]
        return data
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
