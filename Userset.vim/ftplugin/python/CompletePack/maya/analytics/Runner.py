"""
File containing class that handles the process of running analytics,
including management of the options for running.
"""
#======================================================================
import os
import json
import time
import maya.cmds as cmds

__all__ = ['Runner']

from .utilities import list_analytics
from .utilities import analytic_by_name
from .maya_file_generator import maya_file_generator, get_maya_files
from .ObjectNamer import ObjectNamer
from .ProgressMatrix import ProgressMatrix
from .Logger import Logger

class Runner(object):
    """
    Class containing information required to run analytics, including
    options and temporary state information.

    Class Members You Can Set
    {
        analytics      : List of names of all analytics to be run.
                         Default: [] (run all available analytics)
        descend        : If True then for all directories that are included in
                         "paths" also include all of the subdirectories below them.
                         Default: True
        force          : If True run the analytic even if up-to-date results exist.
                         Default: False
        return_json    : If True then return all JSON results from the analytics,
                         aggregated by indexing them on the file and analytic name.
                         Use with caution as long runs can make this string huge.
                         Default: False
        list_only      : True means list the analytics to be run and the files to
                         run them on without actually running the analytic.
                         Return value will be a dictionary of {FILE, [ANALYTICS]}
                         Default: False
        paths          : List of paths on which to run the analytics. If
                         any elements are directories they will be walked
                         to find matching files. Use in conjunction with
                         "descend" to find all files below a root directory.
                         Default: []
        report_progress: If True then put up a progress report dialog while
                         running. This works for the list_only mode as well
                         since that too could take some time on a large tree.
                         Default: False
        results_path   : If specified then dump the analytics with this
                         directory as the root. Otherwise use the subdirectory
                         "MayaAnalytics" in the same directory as the file(s)
                         Default: None
        skip           : List of file patterns to ignore when walking directories.
                         e.g. ".mb$" to ignore all Maya Binary files, or
                         "/reference/" to ignore everything in the subdirectory
                         named "reference". Forward-slash separator is assumed.
                         Default: []
        static         : If True then run the Static analytics, otherwise run the
                         scene-based analytics. When Static analytics are run
                         if "paths" are specified a ValueError exception is
                         raised.
                         Default: False
        logger       : Message output destination.
                         Default: message object pointing to stdout
    }

    Analytic Options, used here and/or passed in to analytics
    Add new options by calling Runner.set_option( 'name', 'value' )
    {
        summary:    Include a summary of the output (usually a list of counts)
                    Default: False
        details:    Include full details in the output.
                    Default: False
        anonymous : True if identifying information is to be made
                    anonymous. At the top level this will include file
                    and directory names, for example, output the path
                    "dir1/dir2/file1.ma" instead of "scene1/shot2/dinosaur.ma"
                    Individual analytics may add other anonymizers, for
                    example anonymizing the names of nodes.
                    Default: False.
    }

    Simple example for running the "evalManager" analytic on all files below
    directory "/Volumes/animFiles/filesToAnalyze", dumping the output in the
    sibling directory "/Volumes/animFiles/filesToAnalyze_MayaAnalytics".

        import maya.analytics.Runner as Runner
        runner = Runner()
        runner.analytics = ['EvalManager']
        runner.paths = ['/Volumes/animFiles/filesToAnalyze']
        runner.results_path = '/Volumes/animFiles/filesToAnalyze_MayaAnalytics'
        runner.report_progress = True
        runner.run()
    """
    #----------------------------------------------------------------------
    def __init__(self):
        """
        Start out the analytic options with all defaults
        """
        self.analytics = []
        self.descend = True
        self.force = False
        self.list_only = False
        self.report_progress = False
        self.paths = []
        self.results_path = None
        self.skip = []
        self.static = False
        self.return_json = False
        self.logger = Logger()
        #
        self.options = { 'details'   : False,
                         'summary'   : False,
                         'anonymous' : False }

        # This will be filled in when the options are set
        self.files_to_process = []

    #----------------------------------------------------------------------
    def __str__(self):
        """Pretty-print the current options"""
        result = 'Analytic Runner\n'
        result += 'Paths       [%s]\n' % str(self.paths)
        result += 'Analytics   [%s]\n' % str(self.analytics)
        result += 'Skip List   [%s]\n' % str(self.skip)
        result += 'Results     [%s]\n' % str(self.results_path)
        result += 'Force       [%s]\n' % str(self.force)
        result += 'List-only   [%s]\n' % str(self.list_only)
        result += 'Do Static   [%s]\n' % str(self.static)
        result += 'Descend     [%s]\n' % str(self.descend)
        result += 'Anonymous   [%s]\n' % str(self.options['anonymous'])
        result += 'Progress    [%s]\n' % str(self.report_progress)
        result += 'Summary     [%s]\n' % str(self.options['summary'])
        result += 'Details     [%s]\n' % str(self.options['details'])
        result += 'JSON Return [%s]\n' % str(self.return_json)
        return result

    #----------------------------------------------------------------------
    def __warning(self, msg):
        """Common interface to warning logger"""
        if self.logger:
            self.logger.warning( msg )

    #----------------------------------------------------------------------
    def __error(self, msg):
        """Common interface to error logger"""
        if self.logger:
            self.logger.error( msg )

    #----------------------------------------------------------------------
    def __debug(self, msg):
        """Common interface to debug logger"""
        if self.logger:
            self.logger.debug( msg )

    #----------------------------------------------------------------------
    def __log(self, msg):
        """Common interface to logger"""
        if self.logger:
            self.logger.log( msg )

    #----------------------------------------------------------------------
    def __indent(self, level_change):
        """Common interface to logger indentation modifier"""
        if self.logger:
            self.logger.indent( level_change )

    #----------------------------------------------------------------------
    def __analytics_to_run(self):
        """
        Return the list of analytics to be run based on the options.
        """
        return_list = []
        # If the analytic names were listed then look them up to check that the
        # is_static flag has the right value
        if type(self.analytics) is list:
            for analytic_name in self.analytics:
                try:
                    analytic = analytic_by_name( analytic_name )
                    if self.static == analytic.is_static:
                        new_analytic = analytic()
                        new_analytic.logger = self.logger
                        return_list.append( new_analytic )
                except Exception, ex:
                    self.__warning( 'Named analytic {} not found ({}), skipping'.format(analytic_name,ex) )
        # Otherwise walk all of the analytics looking for matching ones
        else:
            for (analytic_name, analytic) in list_analytics().iteritems():
                try:
                    if self.static == analytic.is_static:
                        new_analytic = analytic()
                        new_analytic.logger = self.logger
                        return_list.append( new_analytic )
                except ValueError, ex:
                    self.__warning( 'Listed analytic {} not found ({}), skipping'.format(analytic_name,ex) )
        return return_list

    #----------------------------------------------------------------------
    def __files_to_analyze(self):
        """
        Get the list of 3-tuples of Maya files to be analyzed. The tuples are:
            - file to be analyzed
            - the last modified time of the file
            - the directory in which analytics for this file are to be stored.

        raises: ValueError when illegal combinations of flags exist.

        It's worth explaining where results where go based on the settings for
        results_path and anonymous. Assume three Maya files in:
            ROOT_DIR/scene1/booboo.ma
            ROOT_DIR/scene1/yogi.ma
            ROOT_DIR/scene1/scenery/jellystone.ma
        with self.paths=['ROOT_DIR']

            Case 1: results_path=None, anonymous=False
                ROOT_DIR/scene1/MayaAnalytics/booboo.ma/
                ROOT_DIR/scene1/MayaAnalytics/yogi.ma/
                ROOT_DIR/scene1/scenery/MayaAnalytics/jellystone.ma/

            Case 2: results_path=None, anonymous=True (not recommended)
                ROOT_DIR/scene1/MayaAnalytics/file1.ma/
                ROOT_DIR/scene1/MayaAnalytics/file2.ma/
                ROOT_DIR/scene1/scenery/MayaAnalytics/file3.ma/

            Case 3: results_path='/Results', anonymous=False
                /Results/scene1/booboo.ma/
                /Results/scene1/yogi.ma/
                /Results/scene1/scenery/jellystone.ma/

            Case 4: results_path='/Results', anonymous=True
                /Results/dir1/file1.ma/
                /Results/dir1/file2.ma/
                /Results/dir1/dir2/file3.ma/

        Note that the location is relative to the self.paths setting so if
        instead self.paths=['ROOT_DIR/scene1'] then Case 4 becomes:

            Case 4: results_path='/Results', anonymous=True
                /Results/file1.ma
                /Results/file2.ma
                /Results/dir1/file3.ma
        """
        # If no paths exist then the assumption is that the current scene is
        # being analyzed. It still needs a results path but the file to load
        # for it will be None.
        if not self.paths:
            results_path = self.results_path
            if results_path is None:
                results_path = os.path.join( os.path.dirname( cmds.file(query=True,expandName=True) ), 'MayaAnalytics' )
            return [(None,0.0,results_path)]

        if self.static:
            raise ValueError( 'Cannot have static analytics with file names listed' )

        # Use the namer to decide what subdirectory analytic path names
        # should be. If it's set to anonymous then they'll all be
        # named something like file_1/, file_2/, ... otherwise they will
        # have the same name as the file from which they were generated.
        namer = ObjectNamer( ObjectNamer.MODE_PATH, self.options['anonymous'] )

        # Use the generator to find all matching files.
        # Using the get_maya_files() utility function makes it easier to
        # figure out where to put analytics for multiple files in the same
        # directory.
        for path in self.paths:
            iterator = maya_file_generator( path, descend=self.descend, skip=self.skip )
            dirList = get_maya_files( iterator )

            files_to_analyze = []
            for (the_dir, the_files) in dirList:
                if self.results_path == None:
                    analytic_dir = os.path.join(the_dir, 'MayaAnalytics')
                else:
                    analytic_dir = self.results_path
                for the_file in the_files:
                    relpath = os.path.relpath(the_dir,path)
                    if relpath == '.':
                        relpath = ''
                    if self.results_path == None:
                        analytic_path = namer.name(the_file)
                    else:
                        analytic_path = namer.name(os.path.join(relpath,the_file))
                    analytic_path = os.path.join( analytic_dir, analytic_path )
                    file_path = os.path.join(the_dir, the_file)
                    file_modified_time = os.path.getmtime(file_path)
                    files_to_analyze.append( (file_path, file_modified_time, analytic_path) )

        return files_to_analyze

    #======================================================================
    def __establish_baselines(self):
        """
        If not analyzing the current scene clear the scene and let all of the
        analytics establish an empty-scene baseline.
        """
        if self.paths:
            cmds.file( force=True, new=True )
            for analytic in self.__analytics_to_run():
                try:
                    analytic.establish_baseline()
                except Exception, ex:
                    analytic.error( 'Failed to establish baseline : {0:s}'.format(str(ex)) )

    #======================================================================
    @staticmethod
    def __should_analytic_run( analytic, maya_file_modified_time ):
        """
        Check to see if the analytic is out of date with the data file, or if
        the analytic did not successfully complete its previous run.

        analytic:                Analytic to be checked
        maya_file_modified_time: File being checked for analysis
        """
        # Analysis of the current scene should always happen
        if maya_file_modified_time == 0.0:
            analytic.debug( 'Analytic running on current scene' )
            return True

        # If the analytic file marker exists the analytic has to be re-run
        if os.path.exists(analytic.marker_file()):
            analytic.debug( 'Evaluating analytic with marker file {0:s}'.format(analytic.marker_file()) )
            return True

        # Check analytic output times against the data file time.
        # If any analytic output file is older than the data file it needs
        # to be regenerated. Any one file being older forces all to be
        # regenerated since we can't be sure of the relationship between
        # the generated files.
        for analytic_file in analytic.output_files():

            if not os.path.exists(analytic_file):
                analytic.debug( 'Analytic with no results should run' )
                return True

            analytic_modified_time = os.path.getmtime(analytic_file)
            if analytic_modified_time < maya_file_modified_time:
                analytic.debug( 'Analytic file {0:s} at {1:s} out of date with Maya file {2:s}'.format(
                                analytic_file,
                                time.ctime(analytic_modified_time),
                                time.ctime(maya_file_modified_time) ) )
                return True

        return False

    #======================================================================
    def set_option(self, option_name, option_value):
        """
        Define a new option for analytics to use. All analytics being run
        use the same set of options so put the union of options in here before
        running.

        "summary", "details", and "anonymous", are common boolean options on
        all analytics and already present. Other options can be any data type
        you wish but the analytic is responsible for accessing it.

        The safe way for analytics to extract options is to override the
        analytic's set_options() method, look for the option(s) of interest,
        and set a class variable based on the option settings for use
        during the analytic's run.

        option_name:  Name of option to pass along
        option_value: Current value of the option
        """
        # Implementation is just class members for now but it could change
        # so use the method to set options.
        self.options[option_name] = option_value

    #======================================================================
    def run(self):
        """
        Run analytics as appropriate based on the options present.

        Analytics will return JSON result information to be stored in a file
        named "ANALYTIC.json" and may also create other files they can name
        themselves (e.g. ANALYTIC.png for a screenshot).

        Timing information for running the analytic and, if required, loading
        the file are appended to the JSON output data.
        """
        self.__debug( str(self) )
        start_run_time = cmds.timerX()

        analytics_to_run = self.__analytics_to_run()
        files_to_analyze = self.__files_to_analyze()

        # If self.return_json is true then all of the analytic output will be
        # gathered into this JSON-formatted object that looks like this:
        #
        #   { "analytic_run" : LIST_OF_RESULTS }
        #   LIST_OF_RESULTS = [ { "file" : "FILE_NAME", "analytics" : ANALYTIC_LIST } ]
        #   LIST_OF_ANALYTICS = [ "ANALYTIC_NAME" : { ANALYTIC_OUTPUT } ]
        #
        json_results = {}

        # This will be a dictionary of {FILE,[ANALYTICS]} containing every
        # combination that was run. It's used to dump the information in
        # the list_only mode.
        combinations_run = {}

        # If loading files then give the analytics a chance to establish an
        # empty file baseline. If not loading files the analytic will have to
        # figure some other way to establish a baseline.
        self.__establish_baselines()

        # Create the progress reporter, even if no reporting will be done.
        # It's cheap and avoids a bunch of extra 'if' statements.
        progress_reporter = ProgressMatrix( [len(files_to_analyze), len(analytics_to_run)],
                               title='Total files= {0:d}, Total analytics = {1:d}'.format( len(files_to_analyze),
                                                                                           len(analytics_to_run) ),
                                            progress_fmt='File {0:d}, Analytic {1:d}' )
        progress_reporter.enabled = self.report_progress
        progress_reporter.start()
        file_load_time = 0.0
        file_number = 0
        analytic_count = 0
        for (maya_file,file_modified_time,analytic_directory) in files_to_analyze:
            self.__debug( 'Running analytics on file "{0:s}"'.format( maya_file ) )
            self.__indent(1)
            json_per_file = {}

            # A file of "None" means analyze the current scene, so it's
            # already loaded in that case.
            file_is_loaded = (maya_file is None)

            # Loop through all analytics on the currently loaded file, running
            # them if necessary.
            analytic_number = 0
            for analytic in analytics_to_run:
                analytic.debug('Starting analytic')
                self.__indent(1)
                try:
                    analytic.set_output_directory( analytic_directory )
                    analytic.set_options( self.options )
                    progress_reporter.report( [file_number, analytic_number] )
                    analytic_number += 1

                    # Check to see if any analytic file is out of date with the data file.
                    # Analytics on the current scene are assumed always out of date
                    if not self.__should_analytic_run( analytic, file_modified_time ):
                        self.__debug( 'Skipping' )
                        self.__indent( -1 )
                        continue

                    # This just lets us avoid counting them all later
                    analytic_count += 1

                    # That's far enough if we're just listing the analytics
                    # that would run.
                    combinations_run[maya_file] = combinations_run.get(maya_file,[]) + [analytic.name()]
                    if self.list_only:
                        self.__debug( 'Listing only' )
                        self.__indent( -1 )
                        continue

                    # By delaying the loading of the file we can skip loading
                    # any files that have no pending analytics.
                    if not file_is_loaded:
                        try:
                            self.__debug( 'Loading file {0:s}'.format(maya_file) )
                            start_time = cmds.timerX()
                            cmds.file( maya_file, open=True, force=True, prompt=False )
                            file_load_time = cmds.timerX( st=start_time )
                            file_is_loaded = True
                        except Exception, ex:
                            self.__error( 'Problems reading test file "{0:s}" : {1:s}'.format(maya_file, str(ex)) )

                    # Time the analytic, adding the timing information to the
                    # JSON output data
                    start_time = cmds.timerX()

                    json_output = analytic.run()
                    if json_output is None:
                        json_output = {}

                    # For backwards compatibility embed the former CSV output
                    # into the JSON data. It's easily extracted by name.
                    if analytic.csv_output:
                        analytic.debug( 'Appending the old-style CSV output' )
                        json_output['csv'] = '\n'.join(analytic.csv_output)

                    json_data = { 'output' : json_output }

                    # Time the analytic, append the timing information to
                    # the returned JSON and write it out to the analytic file
                    elapsed_time = cmds.timerX( st=start_time )

                    # Add in the options used for this run
                    json_data['options'] = self.options

                    # Total elapsed run time for this analytic
                    json_data['run_time'] = elapsed_time

                    # Total elapsed file load time for this analytic, if it
                    # loaded a file at all.
                    if file_load_time > 0.0:
                        json_data['file_load_time'] = file_load_time

                    json_data = { analytic.name() : json_data }

                    analytic.debug( 'Analytic elapsed time is {0:f}'.format( elapsed_time ) )
                    analytic.debug( 'Output files {0:s}'.format( analytic.output_files() ) )

                    # The JSON output is dumped here. The analytic is free to
                    # provide no return values and handle all of the output
                    # itself, though it cannot use the .json file to do so.
                    # (e.g. it could do a screen dump and not return anything)
                    # There is still the timing information to dump though so
                    # even if no extra output is provided the JSON will be
                    # written.
                    try:
                        with open(analytic.json_file(), 'w') as json_fd:
                            # Add indentation so that the output is at least a
                            # little bit human-readable, even though that's not
                            # the main intent.
                            json.dump( json_data, json_fd, indent=4 )
                    except IOError, ex:
                        analytic.error( 'Could not write JSON output to {0:s} ({1:s}'.format(
                                        analytic.json_file(), str(ex) ) )

                    if self.return_json:
                        json_per_file[analytic.name()] = json_data

                except Exception, ex:
                    analytic.error( 'Unknown failure: "{0:s}"'.format(ex) )

                self.__indent(-1)

            if self.return_json:
                json_results[maya_file] = { 'analytics' : json_per_file }

            self.__indent(-1)
            file_number += 1

        progress_reporter.end()
        total_elapsed_time = cmds.timerX( st=start_run_time )

        # Always list what was run. In the list_only case this is the only output
        if len(combinations_run) > 0:
            print json.dumps( combinations_run, indent=4 )
            print 'Analytics: {0:d}\nFiles    : {1:d}\nTime     : {2:f} seconds'.format(
                    analytic_count, len(combinations_run), total_elapsed_time )
        else:
            print 'No Analytics run'

        if self.return_json:
            return { 'analytic_run' : json_results }

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
