"""
Package definition for mayabullet

Copyright (C) 2011 Autodesk, Inc.  All rights reserved.

Developer Tip:
To auto-reload the entire package when maya is running, a shelf button can be
created with the following content.

import sys
bulletScriptPath = '<Bullet src location>/Bullet/scripts'
if (not bulletScriptPath in sys.path):
    sys.path.insert(0,bulletScriptPath)

import maya.app.mayabullet
import maya.app.mayabullet.BulletUtils
import maya.app.mayabullet.CommandWithOptionVars
import maya.app.mayabullet.Ragdoll
import maya.app.mayabullet.RigidBody
import maya.app.mayabullet.RigidBodyConstraint
import maya.app.mayabullet.SoftBody
import maya.app.mayabullet.SoftBodyConstraint

reload(maya.app.mayabullet)
reload(maya.app.mayabullet.BulletUtils)
reload(maya.app.mayabullet.CommandWithOptionVars)
reload(maya.app.mayabullet.Ragdoll)
reload(maya.app.mayabullet.RigidBody)
reload(maya.app.mayabullet.RigidBodyConstraint)
reload(maya.app.mayabullet.SoftBody)
reload(maya.app.mayabullet.SoftBodyConstraint)
"""

# NOTE: Not recommended to import specific functions instead of entire module
#       Cannot reload() a function, but can do it for a module
#
# REFERENCE: http://docs.python.org/library/functions.html#reload
#
# If a module imports objects from another module using from ... import ...,
# calling reload() for the other module does not redefine the objects imported
# from it one way around this is to re-execute the from statement, another is
# to use import and qualified names (module.*name*) instead.
#
# In other words, avoid doing this:
#     from mayabullet.Ragdoll import addCapsulesToSkeleton
# Logging setup. Use mayabullet.logger within this package.
import logging
logger = logging.getLogger( __name__ )
logger.setLevel( logging.WARN )
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
