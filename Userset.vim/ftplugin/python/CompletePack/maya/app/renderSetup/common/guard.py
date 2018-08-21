"""Contexts and decorators to implement guards.

This module implements guards that can be used to transiently set and
restore data in an exception-safe and maintenance-friendly way.

Context objects in this module can be used in the Python 'with' statement
to ensure that finalization is always done, regardless of how the 'with'
statement code block is exited.

Decorators in this module use the context objects to provide a convenient
syntax to guard a block that is a complete function."""

class MemberGuardCtx:
    """Safe way to transiently set and restore one or more class instance's
    data member(s) using the 'with' statement.  It will restore the data
    member(s) previous value(s) on exit from the block.

    The data member is specified by string name.  When used for multiple
    data members, a dictionary is given to the guard, with the keys as
    the data member string names, and the dictionary values as the new
    values.
    
    Single member example:
        obj.a = oldValue
        # Set obj.a to newValue for this scope.
        with MemberGuardCtx(obj, 'a', newValue):
            # obj.a == newValue
            obj.whatever()
        # At this point, obj.a == oldValue

    Multiple member example:
        obj.a = oldValue
        obj.b = 'oldStringValue'
        # Set obj.a and obj.b to new values for this scope.
        with MemberGuardCtx(obj, {'a': newValue, 'b': 'newStringValue'}):
            # obj.a == newValue
            # obj.b == 'newStringValue'
            obj.whatever()
        # At this point, obj.a == oldValue, obj.b == 'oldStringValue'

    If the caller supplies a member name that does not exist, or a single
    argument that is not a dictionary, KeyError is raised."""

    def __init__(self, obj, member, newVal=None):
        self.objDict = obj.__dict__
        self.member = member
        self.singleMember = isinstance(self.member, basestring)
        if self.singleMember:
            self.newVal = newVal
        else:
            self.oldVal = {}

    def __enter__(self):
        if self.singleMember:
            self.oldVal = self.objDict[self.member]
            self.objDict[self.member] = self.newVal
        else:
            # member must be a dictionary.
            for key in self.member:
                self.oldVal[key] = self.objDict[key]
                self.objDict[key] = self.member[key]
        return None

    def __exit__(self, type, value, traceback):
        if self.singleMember:
            self.objDict[self.member] = self.oldVal
        else:
            for key in self.member:
                self.objDict[key] = self.oldVal[key]

def member(objectMember, newValue=True):
    """Set a data member to a fixed value within the scope of the decorated
member member."""

    # See undo module for decorator comments.

    def decorator(f):
        def wrapper(*args, **kwargs):
            # args[0] is the object, self in the method member definition. 
            with MemberGuardCtx(args[0], objectMember, newValue):
                return f(*args, **kwargs)
        return wrapper
    return decorator

class StateGuardCtx:
    """Safe way to transiently call set and get method within the scope of a function
    The get and set functions must be callables.
    
    Example:
        static def getSomeState(state):
            return someStaticState

        static def setSomeState(state):
            someStaticState = state

        setSomeStaticState(oldValue)

        # Set someStaticState to newTempValue for this scope.
        with StateGuardCtx(getSomeState, setSomeState, newTempValue):
            # someStaticState == newTempValue
            doSomeWork()
        # At this point, someStaticState == oldValue """

    def __init__(self, getFunc, setFunc, newVal=None):
        self.getFunc = getFunc
        self.setFunc = setFunc
        self.newVal = newVal
        self.oldVal = None

    def __enter__(self):
        self.oldVal = self.getFunc()
        self.setFunc(self.newVal)
        return None

    def __exit__(self, type, value, traceback):
        self.setFunc(self.oldVal)

def state(getFunc, setFunc, newValue=True):
    """Set a static state to a fixed value within the scope of the decorated function."""

    # See undo module for decorator comments.

    def decorator(f):
        def wrapper(*args, **kwargs):
            # args[0] is the object, self in the method member definition. 
            with StateGuardCtx(getFunc, setFunc, newValue):
                return f(*args, **kwargs)
        return wrapper
    return decorator

import os

class EnvironGuardCtx:
    """Safe way to transiently set and restore an environment variable
    using the 'with' statement.  If the environment variable existed
    previously, its value is restored on exit from the block.  If the
    environment variable did not exist before, it is removed from the
    environment on exit from the block.
    
    Example:
        import os
        os.environ['a'] = 'oldValue'
        # Set os.environ['a'] to 'newValue' for this scope.
        with EnvironGuardCtx('a', 'newValue'):
            # os.environ['a'] == 'newValue'
        # At this point, os.environ['a'] == 'oldValue'

    Unsetenv example:
        import os
        # Assume os.environ['a'] does not exist.
        # Set os.environ['a'] to 'newValue' for this scope.
        with EnvironGuardCtx('a', 'newValue'):
            # os.environ['a'] == 'newValue'
        # At this point, os.environ['a'] does not exist."""

    def __init__(self, key, value):
        self.unsetenv = key not in os.environ
        self.key      = key
        self.value    = value
        self.oldValue = None

    def __enter__(self):
        if not self.unsetenv:
            self.oldValue = os.environ[self.key]
        os.environ[self.key] = self.value
        return None

    def __exit__(self, type, value, traceback):
        if self.unsetenv:
            del os.environ[self.key]
        else:
            os.environ[self.key] = self.oldValue

def environ(key, value):
    """Set an environment variable to a value within the scope of the decorated
member.

    On scope exit, the previous value is restored.  If the environment
    variable did not exist, it is removed from the environment."""

    # See undo module for decorator comments.

    def decorator(f):
        def wrapper(*args, **kwargs):
            with EnvironGuardCtx(key, value):
                return f(*args, **kwargs)
        return wrapper
    return decorator
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
