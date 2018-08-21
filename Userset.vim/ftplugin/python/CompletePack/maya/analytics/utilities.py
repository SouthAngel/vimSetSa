"""
Collection of general utilities for use with Maya analytics. See the help
string for each method for more details.

    list_analytics              : List all of the available analytics
"""
#----------------------------------------------------------------------
import sys
import pkgutil
import importlib

__all__ = [ 'add_analytic'
          , 'bootstrap_analytics'
          , 'analytic_by_name'
          , 'list_analytics'
          ]

ANALYTIC_DEBUGGING = False
ALL_ANALYTICS = {}

#----------------------------------------------------------------------

def add_analytic(name, cls):
    """
    Add a new analytic to the global list. Used by the decorator
    'makeAnalytic' to mark a class as being an analytic.
    """
    ALL_ANALYTICS[name] = cls

#----------------------------------------------------------------------

def bootstrap_analytics():
    """
    Bootstrap loading of the analytics in the same directory as this script.
    It only looks for files with the prefix "analytic" but you can add any
    analytics at other locations by using the @makeAnalytic decorator for
    per-file analytics or the @make_static_analytic decorator for analytics
    that are independent of scene content, and importing them before calling
    list_analytics.
    """
    package = sys.modules[globals()['__package__']]
    for _,modname,_ in pkgutil.walk_packages(path=package.__path__
                                             ,prefix=package.__name__+'.'
                                             ,onerror=lambda x: None):

        if len(modname) < 9:
            # Short names won't have the 'analytic' prefix so skip them
            continue

        prefix_name = modname.split('.')[-1][:8]
        if prefix_name == 'analytic' or prefix_name == 'Analytic':
            # The act of importing will make the @makeAnalytic or
            # @make_static_analytic decorators register the analytic
            # properly.
            importlib.import_module( modname, package )

#----------------------------------------------------------------------

def list_analytics():
    """
    List all of the objects in this packages that perform analysis of the
    Maya scene for output. They were gleaned from the list collected by
    the use of the @makeAnalytic decorator.

    The actual module names are returned. If you imported the module with a
    shorter alias use that instead.
    """
    return ALL_ANALYTICS

#----------------------------------------------------------------------

def analytic_by_name(analyticName):
    """
    Get an analytic class object by name. If no anaytic of that name exists
    then a KeyError exception is raised.
    """
    if analyticName not in ALL_ANALYTICS:
        raise KeyError( 'Analytic "%s" not registered' % analyticName )
    return ALL_ANALYTICS[analyticName]

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
