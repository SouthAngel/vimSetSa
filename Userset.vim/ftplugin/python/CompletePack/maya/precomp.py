#!/usr/bin/env python

import os, tempfile, imp, string
from maya import mel

tempPrecompFilePath = tempfile.mktemp(".precomp")
tempPrecompFilePath = string.replace(tempPrecompFilePath,"\\","/");
mel.eval('performExportToPrecompFile "%s" 0' % tempPrecompFilePath)

precompmodule = imp.load_source("precompmodule", tempPrecompFilePath)
from precompmodule import *

os.unlink(tempPrecompFilePath)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
