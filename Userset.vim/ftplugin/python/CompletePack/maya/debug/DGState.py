"""
Utility to contain the DG state information captured by a correctness
analysis. It reads the information from a file and provides analysis
tools, such as comparison.

State information is in JSON format for easy storage, parsing, and comparison.
Data is stored in a method that provides a parsing clue for what types of
values are stored on the plug:
    isinstance(VALUE, numbers.Number) : Simple numeric value
    type(VALUE) is list : List of simple numeric values (matrix or vector)
    type(VALUE) is dict : Named data type, with a named parser

    {
        "state" :
        {
            "file" : "NAME_OF_FILE",
            "time" : "TIME_AND_DATE_OF_STATE_CAPTURE",
            "dirty" :
            {
                "connections" : [ LIST_OF_ALL_DIRTY_CONNECTIONS ],
                "data" : [ LIST_OF_ALL_DIRTY_DATA_PLUGS ]
            },
            "data" :
            {
                NODE :
                {
                    PLUG : PLUG_VALUE,
                    PLUG : [ PLUG_MATRIX ],
                    PLUG : { "mesh" : { MESH_DATA } },
                    ...
                },
                ...
            },
            "screenshot" : FILE_WHERE_SCREENSHOT_IS_SAVED
        }
"""

import os
import re
import sys
import json
import math
import hashlib
import subprocess
import maya.cmds as cmds

__all__ = [ 'DGState' ]

# Expression that extracts the root attribute out of a full plug name.
RE_ROOT_ATTRIBUTE = re.compile( r'([^\.^\[]+)' )

# Expression that extracts image compare data from the imf_diff output
RE_IMF_IDENTICAL = re.compile( r'.*are identical', re.MULTILINE|re.DOTALL )
RE_IMF_COMPARE = re.compile( r'differing pixels:\s+([0-9\.]+)[^\(]+\(([0-9]+)[^0-9]+([0-9]+)' )

# Expression that extracts image compare data from the ImageMagick output
RE_IMG_COMPARE = re.compile( r'([e0-9\.-]+)\s+\(([e0-9\.-]+)\)' )

# The MD5 block size, optimized for the file system block size (8 * 4k).
MD5_BLOCKSIZE = 33024

# Default value if the md5 could not be calculated. Any default is good,
# this one is at least informative in the human-readable text diffs.
#
# MD5_AS_DEFAULT_COMPARATOR controls whether, when all other comparators
# fail, MD5 should be used to report a difference between two images.
# It is off by default since it generates too many false positives.
MD5_DEFAULT = 'md5'
MD5_AS_DEFAULT_COMPARATOR = False

# Image compare tolerance, in absolute values. It should be high enough to pass
# tolerance for subtle changes like vertex positions being 0.01% different, or
# lights positioned slightly higher or lower within tolerance, but low enough
# for small but important position or colour changes to register.
#
# This number was heuristically determined by examining the differences
# between existing images that were deemed close enough. For comparison
# the FUZZ metric has a value of 65535 when comparing an all-black against
# an all-white image.
IMAGEMAGICK_MATCH_TOLERANCE = 500
IMAGEMAGICK_METRIC = 'FUZZ'

# Image compare tolerance for percentage of differing pixels in imf_diff.
# This is a cruder measurement than ImageMagick, which is why the former is
# given preference if available. The comparison is looking at the percentage
# of differing pixels that are at least the MIN_DIFFERENCE apart in colour.
# The MIN_DIFFERENCE tolerance handles small differences in shading, the
# MATCH_TOLERANCE will help detect shifts in object position or orientation.
IMF_DIFF_MATCH_TOLERANCE = 1.0
IMF_DIFF_MIN_DIFFERENCE = '5'

# Constant indicating that values are completely equal
ALL_SIGNIFICANT_DIGITS_MATCH = 999
# Constant indicating that values are completely unequal
NO_SIGNIFICANT_DIGITS_MATCH = 0
# Number of significant digits to match for regular values
SIGNIFICANT_DIGITS = 1.9
# Number of significant digits to match for inverse matrix values (they are less accurate)
SIGNIFICANT_DIGITS_INVERSE = 0.9

#======================================================================
class DGState(object):
    """
    State object containing all data values that come out of the dbpeek
    command using the 'data' operation for simple data values and the
    dbpeek 'mesh' operation for mesh geometry.

    results_files: Where the intermediate results are stored. None means don't store them.
    image_file:    Where the screenshot is stored. None means don't store it.
    state:         Data state information from the scene.
    """
    # Special placeholder names for plugs when reporting image differences
    SCREENSHOT_NODE     = '__screenShot__'
    # This plug reports the two differing MD5 values
    SCREENSHOT_PLUG_MD5 = '%s.md5' % SCREENSHOT_NODE
    # This plug reports the two (MD5,ImageMagick comparison) values separated by a vertical bar '|'
    SCREENSHOT_PLUG_MAG = '%s.mag' % SCREENSHOT_NODE
    # This plug reports the two (MD5,imf_diff comparison) values separated by a vertical bar '|'
    SCREENSHOT_PLUG_IMF = '%s.imf' % SCREENSHOT_NODE

    # Output modes for the compare() function
    OUTPUT_CSV = 0
    OUTPUT_JSON = 1

    # Name to match for inverse matrix attributes, who use more lenient
    # tolerances when comparing since their computations are less consistent
    RE_INVERSE_MATRIX = 'InverseMatrix'

    #----------------------------------------------------------------------
    def __init__(self):
        """
        Create a new state object.
        """
        self.results_file = None
        self.image_file = None
        self.filtered_plugs = {}
        self.state = []
        self.md5_value = MD5_DEFAULT

    #----------------------------------------------------------------------
    def __str__(self):
        """
        Dump the state as a string. This converts the state CSV into a JSON
        indented format to make it easier to read.
        """
        state = {}
        for state_line in self.state:
            state_info = state_line.split(',')
            state[state_info[0]] = state_info[1:]

        return json.dumps( state, indent=4 )

    #----------------------------------------------------------------------
    def scan_scene(self, do_eval, data_types):
        """
        Read in the state information from the current scene.
        Create a new state object, potentially saving results offline if
        requested.

        do_eval      : True means force evaluation of the plugs before checking
                       state. Used in DG mode since not all outputs used for
                       (e.g.) drawing will be in the datablock after evaluation.
        data_types   : Type of data to look for - {mesh, vertex, number, vector, screen}
                       If screen is in the list the 'image_file' argument must also be specified.
        """
        self.results_file = None
        self.image_file = None
        self.state = []
        self.md5_value = MD5_DEFAULT

        # Translat the method args into arguments for the dbpeek operations
        data_args = []
        mesh_args = ['vertex','verbose']
        if do_eval:
            data_args += ['eval']
            mesh_args += ['eval']
        if 'number' in data_types:
            data_args += ['number']
        if 'matrix' in data_types:
            data_args += ['matrix']
        if 'vector' in data_types:
            data_args += ['vector']

        # The two dbpeek operations both generate CSV data with similar
        # formatting (PLUG,#,#,#...) so a simple join is good enough.
        #
        # More complex data might warrant a more complex algorithm
        # such as splitting the state data into separate objects and
        # comparing them that way.
        #
        # The "[1:]" is to skip the title lines since those are irrelevant.
        #
        self.state = [line for line in cmds.dbpeek( op='data', a=data_args, all=True).strip().split('\n')
                        if line != '\n'][1:]
        if 'mesh' in data_types:
            self.state += [line for line in cmds.dbpeek( op='mesh', a=mesh_args, all=True).strip().split('\n')
                            if line != '\n'][1:]

    #----------------------------------------------------------------------
    def store_state(self, results_file=None, image_file=None):
        """
        Store the existing state in the files passed in.

        results_file: Destination for the raw numerical data for comparison
        image_file:   Destination for the viewport screenshot
        """
        if results_file != None:
            try:
                results_fd = open(results_file, 'w')
                for line in sorted(self.state):
                    if line != '\n':
                        results_fd.write( '%s\n' % line )
                results_fd.close()
            except Exception, ex:
                print 'ERROR: Could not write to results file %s: "%s"' % (results_file, str(ex))

        if image_file != None:
            # Turn off all HUDS for the snapshot since we're only concerned
            # with correct evaluation here
            is_viewcube_visible = cmds.viewManip( query=True, visible=True )
            visibleHUD = [hud for hud in cmds.headsUpDisplay( listHeadsUpDisplays=True )
                if cmds.headsUpDisplay( hud, query=True, vis=True )]
            for hud in visibleHUD:
                cmds.headsUpDisplay( hud, edit=True, vis=False )
            cmds.viewManip( visible=False )

            cmds.refresh( currentView=True, fileExtension='png', filename=image_file )

            # Restore the HUDs that were turned off
            for hud in visibleHUD:
                cmds.headsUpDisplay( hud, edit=True, vis=True )
            if is_viewcube_visible:
                cmds.viewManip( visible=True )

            self.image_file = image_file


    #----------------------------------------------------------------------
    def read_state(self, results_file=None, image_file=None):
        """
        Read in the results from a previous state capture from the given results and
        image files.

        results_file : Name of file from which to load the results.
                       Do not load anything if None.
        image_file   : Name of file from which to load the current viewport screenshot.
                       Do not load anything if None.
        """
        self.results_file = results_file
        self.image_file = image_file
        self.state = []
        # Read the results file state information right away
        if results_file != None:
            try:
                results_fd = open(results_file, 'r')
                for line in results_fd:
                    self.state += [line.rstrip()]
                results_fd.close()
            except Exception, ex:
                print 'ERROR: Could not read results file %s: "%s"' % (results_file, str(ex))

        # Get the MD5 checksum from the image file, if it exists.
        if self.image_file:
            md5_generator = hashlib.md5()
            checksum_fd = open(self.image_file,'rb')
            for chunk in iter(lambda: checksum_fd.read(MD5_BLOCKSIZE), b''):
                md5_generator.update(chunk)
            checksum_fd.close()
            self.md5_value = md5_generator.hexdigest()
        else:
            # Any default is good, this one is at least informative
            self.md5_value = 'MD5'

    #----------------------------------------------------------------------
    def read_graph(self, graph_file):
        """
        Read the graph configuration from a file. If this graph plug list
        exists when doing the comparison then only plugs on the list will
        be considered, otherwise everything will be checked.

        The format of the file is a sequence of nodes followed by their
        attributes demarcated by leading tabs:
            NODE1
                ATTRIBUTE1
                ATTRIBUTE2
                ...
            NODE2
                ATTRIBUTE1
                ATTRIBUTE2
                ...
            ...
        """
        self.filtered_plugs = {}
        try:
            graph_fd = open(graph_file, 'r')
            last_node = None
            for line in graph_fd:
                if line[0] == '\t':
                    if not last_node:
                        raise ValueError( "Attribute found before node" )
                    self.filtered_plugs['%s.%s' % (last_node, line.strip())] = True
                else:
                    last_node = line.strip()
            graph_fd.close()
        except Exception, ex:
            print 'ERR: Could not read graph file %s (%s)' % (graph_file, str(ex))

    #----------------------------------------------------------------------
    @staticmethod
    def __executable(program_name):
        """
        Returns the name of an executable given the program name.
        Mostly done to add the .exe for Windows programs.
        """
        if sys.platform.startswith('win32') or sys.platform.startswith('cygwin'):
            return '%s.exe' % program_name

        return program_name

    #----------------------------------------------------------------------
    @staticmethod
    def __closeness(first_num, second_num):
        """
        Returns measure of equality (for two floats), in unit
        of decimal significant figures.
        """
        # Identical results are obviously equal
        if first_num == second_num:
            return float('infinity')

        # Arbitrarily pick two near-zero values for rounding.
        # This avoids the instability of the log10 method when near zero.
        if abs(first_num) < 1e-4 and abs(second_num) < 1e-4:
            return float('infinity')

        # Standard numerical closeness check, the logarithmic
        # difference of the average divided by the difference gives
        # the number of significant digits they have in common.
        difference = abs(first_num - second_num)
        avg = abs(first_num + second_num)/2
        return math.log10( avg / difference )

    #----------------------------------------------------------------------
    def __compare_list_of_floats(self, float_list1, float_list2):
        """
        Compare two space-separated lists of floating point numbers.
        Return True if they are the same, False if they differ.

        float_list1:        First list of floats
        float_list1:        Second list of floats

        Returns the worst match, in significant digits (0 means no match at all).
        """
        if float_list1 == float_list2:
            return ALL_SIGNIFICANT_DIGITS_MATCH

        worst_match = ALL_SIGNIFICANT_DIGITS_MATCH

        # Values are not trivially equal so compare numerically.
        float_list1_values = float_list1.split(' ')
        float_list2_values = float_list2.split(' ')

        # Obviously if the float Lists have different lengths they are different
        if len(float_list1_values) != len(float_list2_values):
            return NO_SIGNIFICANT_DIGITS_MATCH

        for float_el in range(len(float_list1_values)):
            try:
                tolerance = self.__closeness(float(float_list1_values[float_el])
                                           , float(float_list2_values[float_el]))
                if tolerance < worst_match:
                    worst_match = tolerance
            except ValueError:
                # This indicates non-numerical values in the float list. Since
                # they are undefined they can be assumed to be different.
                return NO_SIGNIFICANT_DIGITS_MATCH

        return worst_match

    #----------------------------------------------------------------------
    def filter_state(self, plug_filter):
        """
        Take the current state information and filter out all of the plugs
        not on the plug_filter list. This is used to restrict the output to
        the set of plugs the EM is evaluating.

        plug_filter: Dictionary of nodes whose values are dictionaries of
                    root level attributes that are to be used for the
                    purpose of the comparison.

                    None means no filter, i.e. accept all plugs.
        """
        new_state = []
        for line in self.state:
            try:
                column_values = line.split(',')
                node = column_values[0]
                attribute = column_values[1]
                if plug_filter:
                    try:
                        if node not in plug_filter:
                            continue
                        attribute = RE_ROOT_ATTRIBUTE.match(attribute).group(1)
                        if attribute not in plug_filter[node]:
                            continue
                    except KeyError:
                        # If members aren't in the dictionaries then they are acceptable.
                        pass
                new_state.append( line )
            except IndexError:
                print 'ERROR: dbpeek line not could not be parsed: "%s"' % line
        self.state = new_state

    #----------------------------------------------------------------------
    def get_md5(self):
        """
        Get the md5 checksum from the image file, if it exists.
        Return '' if the image file wasn't generated for an easy match.
        """
        try:
            if self.image_file:
                md5_generator = hashlib.md5()
                checksum_fd = open(self.image_file,'rb')
                for chunk in iter(lambda: checksum_fd.read(MD5_BLOCKSIZE), b''):
                    md5_generator.update(chunk)
                checksum_fd.close()
                self.md5_value = md5_generator.hexdigest()
        except Exception:
            # If the file could not be read then it may not have been written.
            # Give it the default md5 value
            self.md5_value = MD5_DEFAULT

        return self.md5_value

    #----------------------------------------------------------------------
    def __compare_with_ImageMagick( self, other ):
        """
        Compare the images generated as screenshots using the ImageMagick
        'compare' utility.

        Returns either None if a comparison was not made or the images matched,
        or this CSV difference string if the images were different:

              SCREENSHOT_NODE.mag,ORIG_MD5|ABSOLUTE_DIFF,OTHER_MD5|NORMALIZED_DIFF

        Both absolute and normalized differences are dumped even though only
        the normalized difference is used for the match.
        """
        try:
            compare = self.__executable( 'compare' )
            image_compare_output = subprocess.Popen(
                                    [ compare
                                    , '-metric', IMAGEMAGICK_METRIC
                                    , self.image_file
                                    , other.image_file
                                    , 'null:'
                                    ]
                                    , stdin=subprocess.PIPE
                                    , stderr=subprocess.PIPE
                                    , stdout=subprocess.PIPE).communicate()

            # Return value, if successfully run, will be in this format:
            #
            #     ABS_ERROR (NORMALIZED_ERROR)
            #
            # Experimental comparisons have determined that the normalized
            # error is the best to compare and IMAGEMAGICK_MATCH_TOLERANCE
            # is used as a tolerance value for it.

            compare_match = RE_IMG_COMPARE.match( image_compare_output[1] )
            if compare_match:
                # If the images are not within the given tolerance then return them as failures.
                if float(compare_match.group(1)) > IMAGEMAGICK_MATCH_TOLERANCE:
                    return '%s,%s|%s,%s|%s,%d' % ( self.SCREENSHOT_PLUG_MAG
                                                 , self.md5_value,  compare_match.group(1)
                                                 , other.md5_value, compare_match.group(2)
                                                 , NO_SIGNIFICANT_DIGITS_MATCH )
                else:
                    # Mark success by returning an empty string
                    return ''
            else:
                # If stderr had a message then there is some problem
                # with the comparison so print it out for examination and
                # try another comparison method.
                print 'ERROR: ImageMagick generated the error %s' % image_compare_output[1]
        except Exception, ex:
            print 'WARNING: ImageMagick compare could not be run : "%s"' % str(ex)

        # Mark failure to run by returning None
        return None

    #----------------------------------------------------------------------
    def __compare_with_imf_diff( self, other ):
        """
        Compare the images generated as screenshots using the Maya MentalRay
        'imf_diff' utility.

        Returns either None if a comparison was not made or the images matched,
        or this CSV difference string if the images were different:

              SCREENSHOT_NODE.imf,ORIG_MD5|PERCENT_DIFF,OTHER_MD5|TOTAL_DIFF/TOTAL_PIXELS
        """
        try:
            imf_diff = self.__executable( os.path.join( os.getenv('MENTALRAY_BIN_LOCATION'), 'imf_diff' ) )
            image_compare_output = subprocess.Popen(
                                      [ imf_diff
                                      , '-m', IMF_DIFF_MIN_DIFFERENCE
                                      , self.image_file
                                      , other.image_file
                                      ]
                                      , stdin=subprocess.PIPE
                                      , stderr=subprocess.PIPE
                                      , stdout=subprocess.PIPE).communicate()

            # The output if the images are identical, which only happens when
            # all pixels are within IMF_DIFF_MIN_DIFFERENCE, looks like this:
            #
            #   Image1.png Image1.png: no differences.
            #   == "Image1.png" and "Image1.png" are identical
            #
            if RE_IMF_IDENTICAL.match( ''.join(image_compare_output) ):
                return ''

            # If the images are different the output looks like this:
            #
            #   differing pixels:	  2.755% (30075 of 1091574)
            #   average difference:	 33.546%
            #   maximum difference:	 54.112%
            #   Summary: Some pixels differ strongly.
            #   == "Image1.png" and "Image2.png" are different
            #
            # The words "strongly" and "are different" may vary based on
            # tolerance values found but only the numbers are processed
            # anyway. The differing pixels percentage is the one being
            # compared - values above 1% are considered bad. Average and
            # maximum differences don't mean that much in this context so
            # they are ignored.
            #
            compare_match = RE_IMF_COMPARE.match( ''.join(image_compare_output) )
            if compare_match:
                if float(compare_match.group(1)) > IMF_DIFF_MATCH_TOLERANCE:
                    return '%s,%s|%s,%s|%s/%s,%d' % ( self.SCREENSHOT_PLUG_IMF
                                                    , self.md5_value,  compare_match.group(1)
                                                    , other.md5_value, compare_match.group(2), compare_match.group(3)
                                                    , NO_SIGNIFICANT_DIGITS_MATCH )
                else:
                    # Mark success by returning an empty string
                    return ''
        except Exception, ex:
            print 'WARNING: imf_diff could not be run : "%s"' % str(ex)

        # Mark failure to run by returning None
        return None

    #----------------------------------------------------------------------
    def __compare_images(self, other):
        """
        Compare the images generated as screenshots for the two evaluation
        methods. The exact comparison method will depend on what is available
        on the system running this test.

        The cascading levels of comparison are:
            1. Generate md5 values for both files. If equal the images are identical.
            2. Try the ImageMagick 'compare' utility and check for a tolerance:
                  compare -metric MAW IMAGE1 IMAGE2 null:
            3. If ImageMagick was not present try the imf_diff utility that ships with Maya:

        If the ImageMagick library is not present then the imf_diff utility
        shipped with Maya will be used to generate  a comparison. If that
        utility cannot be accessed then the md5 output below will be returned
        as a difference must be assumed since false positives are better than
        false negatives.

              SCREENSHOT_NODE.md5,ORIG_MD5,OTHER_MD5

        If the files were identical or a comparison could not be made return None.
        If one of the image comparisons returned a difference return that.
        Otherwise return the md5 difference string.
        """
        if not self.image_file or not other.image_file:
            return None

        try:
            self_md5 = self.get_md5()
            other_md5  = other.get_md5()

            # Quick success, the files are identical
            if self_md5 == other_md5:
                return None

        except Exception, ex:
            print 'WARNING: Could not generate md5 values for image comparison : "%s"' % str(ex)
            self_md5 = MD5_DEFAULT
            other_md5 = MD5_DEFAULT

        # md5 differs but the files may be "close enough". Run the image
        # comparison utilities to find out how close they are.
        #
        # The return value "None" indicates the comparitor failed, the
        # empty string indicates the images were the same and any other
        # string contains the difference information.
        #
        # First try ImageMagick
        image_diff = self.__compare_with_ImageMagick( other )
        if image_diff != None:
            return image_diff if len(image_diff)>0 else None

        # Next try the imf_diff utility
        image_diff = self.__compare_with_imf_diff( other )
        if image_diff != None:
            return image_diff if len(image_diff)>0 else None

        if MD5_AS_DEFAULT_COMPARATOR:
            # If none of the image comparators generated a useful result then
            # default back to the md5 value as comparison.
            return '%s,%s,%s,%g' % (self.SCREENSHOT_PLUG_MD5, self_md5, other_md5, NO_SIGNIFICANT_DIGITS_MATCH)
        else:
            # Otherwise report no difference found.
            print 'WARNING: Could not compare the images.  No difference will be reported.'
            return None

    #----------------------------------------------------------------------
    def compare(self, other, output_mode):
        """
        Compare two state information collections and return a count of the
        number of differences. The first two fields (node,plug) are used to
        uniquely identify the line so that we are sure we are comparing the
        same two things.

        The 'clean' flag in column 2 is omitted from the comparison since
        the DG does funny things with the flag to maintain the holder/writer
        states of the data.

        other:       Other DGstate to compare against
        output_mode: Type of output to return (DGState.OUTPUT_CSV, DGState.OUTPUT_JSON)
                      modes return a tuple of (ERROR_DETAILS, ERROR_COUNT, WORST_ERROR_METRIC)

                     The ERROR_DETAILS for each mode are:
                         OUTPUT_CSV  : CSV data with each mismatching plug on its own line
                                       PLUG,THIS_STATE_VALUES,COMPARED_STATE_VALUES
                         OUTPUT_JSON : JSON data with each mismatching plug as a key in dictionary:
                                       {
                                           PLUG : { 'match' : ERROR_METRIC
                                                  , 'value' : [THIS_STATE_VALUES]
                                                  , 'other' : [COMPARED_STATE_VALUES]
                                                  }
                                       }
        """
        self_values = {}
        other_values = {}
        for line in self.state:
            try:
                column_values = line.split(',')
                self_values['%s.%s' % (column_values[0],column_values[1])] = ' '.join(column_values[3:])
            except IndexError:
                print 'ERROR: dbpeek line not could not be parsed: "%s"' % line
        for line in other.state:
            try:
                column_values = line.split(',')
                other_values['%s.%s' % (column_values[0],column_values[1])] = ' '.join(column_values[3:])
            except IndexError:
                print 'ERROR: dbpeek line could not be parsed: "%s"' % line

        if output_mode == DGState.OUTPUT_JSON:
            changed_values = {}
        else:
            changed_values = []
        error_count = 0

        worst_match = ALL_SIGNIFICANT_DIGITS_MATCH

        # Find changed values and values in the original version but not in the new one
        for (name,value) in self_values.iteritems():
            if name in other_values:
                # The inverse matrix attribute calculations are less accurate
                # so be more lenient with them.
                if name.find(DGState.RE_INVERSE_MATRIX) >= 0:
                    significant_digits = SIGNIFICANT_DIGITS_INVERSE
                else:
                    significant_digits = SIGNIFICANT_DIGITS
                match_digits = self.__compare_list_of_floats(value, other_values[name])
                if match_digits < significant_digits:
                    error_count += 1
                    if output_mode == DGState.OUTPUT_JSON:
                        changed_values[name] = { 'match' : match_digits
                                               , 'value' : value
                                               , 'other' : other_values[name]
                                               }
                    else:
                        changed_values.append( '%s,%s,%s,%s' % (name, value, other_values[name], match_digits) )
                if match_digits < worst_match:
                    worst_match = match_digits

        # If image files are present run a comparison on them too
        #
        image_compare = self.__compare_images( other )
        if image_compare:
            error_count += 1
            if output_mode == DGState.OUTPUT_JSON:
                info = image_compare.split(',')
                changed_values[info[0]] = { 'match' : info[3]
                                          , 'value' : info[1]
                                          , 'other' : info[2]
                                          }
            else:
                changed_values.append( image_compare )

        return (changed_values, error_count, worst_match)

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
