# Copyright 2012 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk
# license agreement provided at the time of installation or download,
# or which otherwise accompanies this software in either electronic
# or hard copy form.

# The API 2.0 lib is named _OpenMaya_py2 to avoid conflicts with the
# API 1.0 lib (_OpenMaya) and the C++ lib (OpenMaya) during packaging.
#
# However, we don't want users to have to do this:
#
#		import maya.api._OpenMaya_py2
#		maya.api._OpenMaya_py2.MGlobal.displayInfo('contrived example')
#
# we would rather that they could do this:
#
#		import maya.api.OpenMaya
#		maya.api.OpenMaya.MGlobal.displayInfo('contrived example')
#
# To that end we import _OpenMaya_py2 and copy all of the symbols from its
# dictionary to our own, thus making it appear as if they are part of
# our module, which is called 'OpenMaya'.
#
import maya.api._OpenMaya_py2

ourdict = globals()
py2dict = maya.api._OpenMaya_py2.__dict__

for (key, val) in py2dict.iteritems():
    if key not in ourdict:
        ourdict[key] = val
