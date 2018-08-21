"""
Collection of decorators for use with Maya analaytics.
There are three decorators defined here. You should use
all three so that your decorators become easily self-documented.

    @addMethodDocs        # Embed method docs into class docs
    @addHelp            # Print class docs from a method
    @makeAnalytic        # Flag the class as being an analytic
    class MyAnalytic(AnalyticBase):
        ...

"""
#======================================================================
from .utilities import add_analytic

__all__ = [ 'addMethodDocs'
          , 'addHelp'
          , 'makeAnalytic'
          , 'make_static_analytic'
          ]

#======================================================================

def __removeIndentationFromLine(theString,number=1):
    """
    Utility function to remove the leading documentation indentation in a line of text pulled
    from a class method's "__doc__". Presumes that the leading two tabs or 8 spaces are not
    part of the formatted documentation but leaves all other leading spaces. That's why a
    simple lstrip() couldn't be used.

    'number' is the number of indentation levels to remove. An indentation level is presumed
    to be either a single tab or 4 spaces.
    """
    tabString = '\t' * number
    spcString = '    ' * number
    if theString.startswith(tabString):
        return theString[number:]
    elif theString.startswith(spcString):
        return theString[number*4:]
    return theString.lstrip()

#======================================================================

def __removeIndentation(theString,number=1):
    """
    Utility function to remove the leading documentation indentation in a documentation string.
    Presumes that the leading two tabs or 8 spaces are not part of the formatted documentation
    but leaves all other leading spaces. That's why a simple lstrip() couldn't be used.

    'number' is the number of indentation levels to remove. An indentation level is presumed
    to be either a single tab or 4 spaces. Normally you'd have number=2 for class methods and
    number=1 for regular methods.

    Returns a list of lines so that the caller can indent them the way they want.
    """
    #
    #    Remove leading spaces from the full doc string and split into lines
    #        (1) = theString.lstrip().rstrip().split('\n')
    #
    #    Remove the specified amount of leading indentation from each line
    #        (2) [__removeIndentationFromLine(theString,number) for line in (1)]
    #
    return [__removeIndentationFromLine(line,number) for line in theString.lstrip().rstrip().split('\n')]

#======================================================================

def addMethodDocs(cls):
    """
    Class decorator to add method docs to the class.__doc__.
        @addMethodDocs
        class MYCLASS:
            ...
    This won't report methods with a leading underscore so
    use that naming convention to prevent them from being shown.
    """
    # First get the class documentation, where it is defined.
    doc = ''
    for parent in [cls] + [c for c in cls.__bases__]:
        if hasattr(parent, '__doc__'):
            doc += '\n'.join(__removeIndentation( parent.__doc__ ))
            # Try to avoid too much blank space
            if doc[:1] != '\n':
                doc += '\n'

    # Grab the names of all methods not starting with an underscore for documentation
    methodList = [method for method in dir(cls) if callable(getattr(cls, method)) and method[0] != '_']

    #
    #    Rework the list so that each string in the list loses its leading spaces
    #        (1) = __removeIndentation(s,2)
    #
    #    Add in the same amount of indentation for all lines of each method's documentation
    #        (2) = ('\n\t').ljust(len(m)+8).join((1))
    #
    #    It's a lambda function so that it can be run on all method documentation strings in a loop
    #    If the string was a different format then just pass it through directly
    #        (3) = (lambda s,m: (2)) or (lambda s: s)
    #
    # One thing to note is that the indentation level is hardcoded to be normal class or method
    # level. This is good enough for most purposes though you may want to gear your documentation
    # formatting to behave well with this assumption.
    #
    processFunc = (lambda s,m: ('\n\t').ljust(len(m)+5).join(__removeIndentation(s,2))) or (lambda s: s)

    # Method header
    if len(methodList) > 0:
        methodDocs = '\n\tMethods\n\t-------\n'

        # Add all methods and their docs with spacing that makes sense
        methodDocs += '\n'.join(['\t%s : %s\n' %
                            (method.ljust(3),
                            processFunc(str(getattr(cls, method).__doc__),method))
                            for method in methodList])
    else:
        methodDocs = '\n\tNo Methods\n'

    doc += methodDocs
    cls.__fulldocs__ = doc
    return cls

#======================================================================

def addHelp(cls):
    """
    Class decorator to add a static method addHelp() to a class that prints
    out the class.__fulldocs__ string. Use it in conjunction with @addMethodDocs
    to provide a static help method that prints out documentation for all
    exposed methods.
        @addHelp
        class MYCLASS:
            ...
    """

    # Define the static help method to be installed
    @staticmethod
    def class_help():
        """
        Call this method to print the class documentation, including all methods.
        """
        if hasattr(cls, '__fulldocs__'):
            print cls.__fulldocs__
        else:
            print cls.__doc__

    # Install the static method into the decorated class
    cls.help = class_help

    return cls

#======================================================================

def makeAnalytic(cls):
    """
    Class decorator to add a discoverable static method that marks the
    class as being an analytic to run on a scene.
        @makeAnayltic
        class MYCLASS:
            ...
    """
    # Define the static variable that marks the class as an analytic.
    # The value doesn't matter, only existence is checked.
    cls.is_static = False
    cls.ANALYTIC_NAME = cls.__name__[8:]    # [Aa]nalyticXXX name is XXX
    add_analytic(cls.ANALYTIC_NAME, cls)

    return cls

#======================================================================

def make_static_analytic(cls):
    """
    Class decorator to add a discoverable static method that marks the
    class as being an analytic to run statically (i.e. that does not
    pertain to a particular scene).
        @make_static_anayltic
        class MYCLASS:
            ...
    """
    # Define the static variable that marks the class as an analytic.
    # The value doesn't matter, only existence is checked.
    cls.is_static = True
    cls.ANALYTIC_NAME = cls.__name__[8:]    # [Aa]nalyticXXX name is XXX
    add_analytic(cls.ANALYTIC_NAME, cls)

    return cls

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
