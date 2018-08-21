"""
Module containing all of the Animation Analytic classes.

The analytics in this directory are loaded in the bootstrap method, although you
can add analytics from any location using the @makeAnalytic decorator.

    # Get a list of all available analytics
    from maya.analytics import *
    list_analytics()
"""
from .utilities import ( add_analytic
                       , analytic_by_name
                       , bootstrap_analytics
                       , list_analytics
                       )
from .Runner import Runner
from .Logger import Logger

# Import all of the useful analytic utilities for direct use
__all__ = [ 'Runner'
          , 'Logger'
          , 'analytic_by_name'
          , 'list_analytics'
          ]

bootstrap_analytics()
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
