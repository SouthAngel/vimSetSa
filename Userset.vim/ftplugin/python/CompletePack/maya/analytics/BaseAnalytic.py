"""
Contains the base class from which all analytics inherit.
"""
#----------------------------------------------------------------------
import os
from .ObjectNamer import ObjectNamer

__all__ = ['BaseAnalytic', 'OPTION_DETAILS', 'OPTION_SUMMARY', 'OPTION_ANONYMOUS']

# Option to make output much more verbose
OPTION_DETAILS = 'details'
# Option to include summary information
OPTION_SUMMARY = 'summary'
# Option to remove identifying information from output
OPTION_ANONYMOUS = 'anonymous'

#======================================================================

class BaseAnalytic(object):
    """
    Base class for output for analytics.

    The default location for the anlaytic output is in a subdirectory
    called 'MayaAnalytics' in your temp directory. You can change that
    at any time by calling set_output_directory().

    Class static member:
         ANALYTIC_NAME : Name of the analytic

    Class members:
         directory     : Directory the output will go to
         is_static     : True means this analytic doesn't require a file to run
         logger        : Logging object for errors, warnings, and messages
         plug_namer    : Object creating plug names, possibly anonymous
         node_namer    : Object creating node names, possibly anonymous
         csv_output    : Location to store legacy CSV output
         plug_namer    : Set by option 'anonymous' - if True then make plug names anonymous
         node_namer    : Set by option 'anonymous' - if True then make node names anonymous
         __options     : List of per-analytic options
    """
    ANALYTIC_NAME = 'Unknown'
    #----------------------------------------------------------------------
    def __init__(self):
        """
        Start out the analytic with no data and pointing to stdout
        """
        self.directory = None
        self.logger = None
        self.is_static = False
        self.plug_namer = ObjectNamer( ObjectNamer.MODE_PLUG, anonymous=True )
        self.node_namer = ObjectNamer( ObjectNamer.MODE_NODE, anonymous=True )
        self.__options = []
        self.csv_output = []

    #----------------------------------------------------------------------
    def warning(self, msg):
        """
        Utility to standardize warnings coming from analytics.
        """
        if self.logger:
            self.logger.warning( '({0:s}) {1:s}'.format( self.name(), msg ) )

    #----------------------------------------------------------------------
    def error(self, msg):
        """
        Utility to standardize errors coming from analytics.
        """
        if self.logger:
            self.logger.error( '({0:s}) {1:s}'.format( self.name(), msg ) )

    #----------------------------------------------------------------------
    def debug(self, msg):
        """
        Utility to standardize debug messages coming from analytics.
        """
        if self.logger:
            self.logger.debug( '({0:s}) {1:s}'.format( self.name(), msg ) )

    #----------------------------------------------------------------------
    def log(self, msg):
        """
        Utility to standardize logging messages coming from analytics.
        """
        if self.logger:
            self.logger.log( '({0:s}) {1:s}'.format( self.name(), msg ) )

    #----------------------------------------------------------------------
    def name(self):
        """
        Get the name of this type of analytic
        """
        return self.ANALYTIC_NAME

    #----------------------------------------------------------------------
    def marker_file(self):
        """
        Returns the name of the marker file used to indicate that the
        computation of an analytic is in progress. If this file remains
        in a directory after the analytic has run that means it was
        interrupted and the data is not up to date.

        This file provides a safety measure against machines going down
        or analytics crashing.
        """
        return os.path.join( self.directory, '{0:s}.ANALYZING'.format(self.name()) )

    #----------------------------------------------------------------------
    def json_file(self):
        """
        Although an analytic is free to create any set of output files it
        wishes there will always be one master JSON file containing the
        """
        if self.directory is None:
            self.error( 'Cannot get the json_file until the output directory is set' )
            return None
        return os.path.join( self.directory, '{0:s}.json'.format(self.name()) )

    #----------------------------------------------------------------------
    def output_files(self):
        """
        This is used to get the list of files the analytic will generate.
        There will always be a JSON file generated which contains at minimum
        the timing information. An analytic should override this method only
        if they are adding more output files (e.g. a .jpg file).

        This should only be called after the final directory has been set.
        """
        return [ self.json_file() ]

    #----------------------------------------------------------------------
    def establish_baseline(self):
        """
        This is run on an empty scene, to give the analytic a chance to
        establish any baseline data it might need (e.g. the nodes in an
        empty scene could all be ignored by the analytic)

        Base implementation does nothing. Derived classes should call
        their super() method though, in case something does get added.
        """
        pass

    #----------------------------------------------------------------------
    def option(self, option):
        """
        Return TRUE if the option specified has been set on this analytic.
        option: Name of option to check
        """
        return option in self.__options

    #----------------------------------------------------------------------
    def set_options(self, options):
        """
        Modify the settings controlling the run operation of the analytic.
        Override this method if your analytic has some different options
        available to it, but be sure to call this parent version after since
        it sets common options.
        """
        try:
            self.plug_namer = ObjectNamer( ObjectNamer.MODE_PLUG, anonymous=options['anonymous'] )
            self.node_namer = ObjectNamer( ObjectNamer.MODE_NODE, anonymous=options['anonymous'] )
        except KeyError:
            # If no anonymous option keep the previous setting
            pass

        self.__options += options

    #----------------------------------------------------------------------
    def set_output_directory(self, directory):
        """
        Call this method to set a specific directory as the output location.
        The special names 'stdout' and 'stderr' are recognized as the
        output and error streams respectively rather than a directory.
        """
        self.directory = directory

        try:
            try:
                os.makedirs( directory, 0777 )
            except OSError,err:
                # This is the "directory already exists" error; harmless here
                if err.errno!=17:
                    raise

            if not os.access( directory, os.W_OK):
                raise Exception( 'No permission to add files to %s' % directory )

        except Exception, ex:
            self.error( 'Could not create output directory ({0:s})'.format( str(ex) ) )

    #======================================================================
    #
    # All nodes below here are called from the derived analytic class.
    # The convention of a single leading underscore is used to denote this.
    #
    #======================================================================

    #----------------------------------------------------------------------
    def _output_csv(self, data):
        """
        CSV dump of the given data. The data must be a list of values which
        will be dumped in a correct CSV line format.
        """
        try:
            if type(data) != type([]):
                raise TypeError('_output_csv requires a list input')

            self.csv_output.append( ','.join( ['"{0:s}"'.format( str(column) ) for column in data] ) )
        except Exception, ex:
            self.warning( 'Failed to output CSV data: "{0:s}"'.format( str(ex)) )

    #----------------------------------------------------------------------
    def _set_node_name_count(self, max_node_count):
        """
        Define the number of nodes that will be named in this analytic so
        that the appropriate number of leading 0's can be added. For example
        if you set it to 9000 the first node will be 'node0001', but if you
        set it to 90,000 the first node will be 'node00001'.
        """
        self.node_namer.set_max_objects( max_node_count )

    #----------------------------------------------------------------------
    def _node_name(self, original_name):
        """
        Return the node name for output. If the name is not anonymous then
        are being shown the result is just the name itself. Otherwise the
        result is a combination of the node type and a unique ID per type.

        You can get a more consistent name suffix length for anonymous names
        if you first call _set_node_name_count(#) before using this method.

        original_name: Real name of the node in the scene
        """
        return self.node_namer.name( original_name )

    #----------------------------------------------------------------------
    def _set_plug_name_count(self, max_plug_count):
        """
        Define the number of plugs that will be named in this analytic so
        that the appropriate number of leading 0's can be added. For example
        if you set it to 9000 the first plug will be 'node0001.tx', but if you
        set it to 90,000 the first plug will be 'node00001.tx'.
        """
        self.plug_namer.set_max_objects( max_plug_count )

    #----------------------------------------------------------------------
    def _plug_name(self, original_name):
        """
        Return the plug name for output. If the name is not anonymous then
        are being shown the result is just the name itself. Otherwise the
        result is a combination of the node type and a unique ID per type
        plus the attribute(s).

        You can get a more consistent name suffix length for anonymous names
        if you first call _set_plug_name_count(#) before using this method.

        original_name: Real name of the plug in the scene
        """
        return self.plug_namer.name( original_name )

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
