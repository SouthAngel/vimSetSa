"""Profiler guard support.

   This module provides a context manager to have a convenient 
   profiler guard mechanism.  It ensures that the profiler is started 
   and stopped at expected time.
"""

# There is no Python V2 interface for MProfiler so need to use V1 interface.
# Defect MAYA-55923 logged for missing interface.
import maya.OpenMaya as OpenMayaV1


_profilerCategory = OpenMayaV1.MProfiler.addCategory('Render Setup') 
_profilerColor = OpenMayaV1.MProfiler.kColorE_L2


class ProfilerMgr:
    """ Safe way to manage profiler guard
   
    Example:
        with ProfilerMgr('Profile Cube Creation'):
            cmds.polyCube()
            cmds.polyCube()
    """
    
    def __init__(self, name):
        self.name = name if name is not None else 'unnamed'
        self.eventId = None

    def __enter__(self):
        self.eventId = OpenMayaV1.MProfiler.eventBegin(_profilerCategory, _profilerColor, self.name)
        pass

    def __exit__(self, type, value, traceback):
        OpenMayaV1.MProfiler.eventEnd(self.eventId)
        pass

#
#  MAYA-66653: The decorator does not work when there are two decorators at the same level, 
#              the profiler detects correctly the blocks, manages correctly the profile names, 
#              but the profiler window displays the wrong names.
#              In the case below, the profiler window will display 'part2' and 'part2' as children of 'top'
#
#       @profiler.profile
#       def top():
#           part1()
#           part2()
#
#       @profiler.profile
#       def part1():
#           print f.__name__
#
#       @profiler.profile
#       def part2():
#           print f.__name__
#
def profile(decoratedFunc):
    """ Profile decorator to manage the profiling scope
    """

    # Decorator functions always take a single argument (usually the
    # decorated function), so we need to use a layered approach so we can
    # also pass in the profiling name.
    #
    # The decorator function (i.e. "profile") is the function doing
    # the decorating: its single argument is the decorated function, and it
    # returns the wrapper ("funcWrapper") function, which is used instead of
    # the decorated function.  Where the decorated function would have been
    # called, wrapper is now called instead, and it uses the ProfilerMgr context
    # to correctly start and stop the profiler.

    def funcWrapper(*args, **kwargs):
        with ProfilerMgr('%s::%s' % (decoratedFunc.__module__, decoratedFunc.__name__)):
            return decoratedFunc(*args, **kwargs)
    return funcWrapper
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
