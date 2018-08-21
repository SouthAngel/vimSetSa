"""
Contains the Logger class. Creates an interface to log errors, warnings,
debugging, and log messages that allows for indented nesting.
"""

__all__ = ['Logger']

import sys
#----------------------------------------------------------------------
class Logger(object):
    """
    Utility class to allow printing of errors, warnings, and logger with the
    ability to silence everything. The logger are tagged with a prefix that
    lets you easily tell what kind of logger they are.
    """
    def __init__(self, debugging=False, file_name=None):
        """
        Create the Logger object with an initial output state.

        file_name: If not None then the output will go to the named file
        debugging: If True then output debugging and log messages.
                   Default is just to print errors and warnings.
        """
        self.debugging = debugging
        self.log_file = sys.stdout
        self.indentation = ''
        self.indent_level = 0
        if file_name != None:
            try:
                self.log_file = open(file_name, 'w')
            except IOError, ex:
                self.log_file = sys.stdout
                self.error( 'Could not open file %s for write: {0:s}'.format( (str(file_name), str(ex)) ) )

    #----------------------------------------------------------------------
    def __log_message(self, tag, message):
        """
        Print a version of the message with indenting added. The indentation
        is prepended to the string, and inserted anywhere in the string
        following a newline. So a string "a\nb" with indentation of 4 will
        look like:
            a
            b
        Which is much nicer than:
            a
        b

        tag:     Logging type tag, e.g. 'LOG'
        message: Message to be indented
        """
        # The extra spaces account for the logging type, so that in the a\nb
        # example above for an error message you'll see everything lined up:
        #
        # ERR:       a
        #            b
        #
        indented_newline = '\n      {0:s}'.format( self.indentation )
        self.log_file.write( '{0:s}: {1:s}{2:s}\n'.format( tag, self.indentation,
                                           indented_newline.join( message.rstrip().split('\n') ) ) )

    #----------------------------------------------------------------------
    def indent(self, indent_change=1):
        """ Change the indentation level for the output """
        self.indent_level += indent_change
        if self.indent_level < 0:
            self.indent_level = 0
        self.indentation = '    ' * self.indent_level

    #----------------------------------------------------------------------
    def log(self, message):
        """ Print out a message as information """
        if self.debugging:
            self.__log_message( 'LOG ', message )

    #----------------------------------------------------------------------
    def debug(self, message):
        """ Print out a message flagged as debugging information """
        if self.debugging:
            self.__log_message( 'DBG ', message )

    #----------------------------------------------------------------------
    def warning(self, message):
        """ Print out a message as a warning """
        self.__log_message( 'WARN', message )

    #----------------------------------------------------------------------
    def error(self, message):
        """ Print out a message as an error """
        self.__log_message( 'ERR ', message )

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
