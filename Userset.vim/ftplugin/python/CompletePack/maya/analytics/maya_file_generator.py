"""
Utility functions to walk Maya files under a path (file or directory).
"""
import os
import re

__all__ = [ 'maya_file_generator', 'get_maya_files' ]

def maya_file_generator(root_path, skip=None, descend=True):
    """
    Generator to walk all Maya files in or below a specific directory.

    root_path  : Path or list of paths to walk, looking for Maya files
    skip       : A list of regular expression strings indicating path patterns
                 to skip.  Match begins anywhere in the string so the leading
                 "^" is necessary if you wish to check for a prefix. Some
                 example expressions include:

                 '.mb$'         : Skip all Maya Binary files
                 '/references/' : Skip all files in a subdirectory called "references"
                 '_version.*'   : Skip all files with a version number in the name

    descend    : Recurse into subdirectories

    Returns list of filepaths in any of the root_paths not matching the skip patterns.

    Usage:
    Find all Maya files under "root/projects" that aren't temporary files,
    defined as those named temp.ma, temp.mb, or that live in a temp/ subdirectory.

        from maya.analytics.maya_file_generator import maya_file_generator
        for path in maya_file_generator('Maya/projects', skip=['^temp.m{a,b}$','/temp/']):
            print path

        for path in maya_file_generator(['Maya/projects/default','Maya/projects/zombie']):
            print path
    """
    # Keep the compiled patterns handy for speed
    skip_patterns = []
    if skip:
        for pattern in skip:
            skip_patterns.append( re.compile(pattern) )

    #======================================================================
    def __is_path_excluded(path_to_check):
        """
        Check to see if the named path is excluded by the filters.
        Note that this is not applied at the root directory level. It is
        assumed that if you want to exclude the root you won't bother
        calling the iterator.
        """
        if not descend:
            return True

        # Check for any explicitly skipped file path patterns
        for skip_pattern in skip_patterns:
            if skip_pattern.search( path_to_check ):
                return True

        # Ensure these are Maya files
        if os.path.isfile(path_to_check):
            (_,file_ext) = os.path.splitext(path_to_check)
            if file_ext != '.ma' and file_ext != '.mb':
                return True

        return False

    # If just a single path to check put it into a one-item list for simplicity
    root_path_list = root_path if isinstance(root_path, list) else [root_path]

    for root_path in root_path_list:
        for root, dirs, files in os.walk(root_path, topdown=True):
            # The [:] is to overwrite the existing list in place so that descent
            # through excluded directories in os.walk is avoided
            dirs[:] = [d for d in dirs if not __is_path_excluded(d)]
            for name in (f for f in files if not __is_path_excluded(os.path.join(root,f))):
                yield os.path.join(root, name)

#======================================================================
def get_maya_files(generator):
    """
    Help function for the MayaFileGenerator class that runs the generator
    and then packages up the results in a directory-centric format.

    generator : A MayaFileGenerator function call, already constructed but not used

    returns a list of ( DIRECTORY, [FILES] ) pairs consisting of
        all matching files from generation using the passed-in generator.

    theGen = MayaFileGenerator("Maya/projects", skipFiles=['temp\\w'])
    for (the_dir,files_in_dir) in get_maya_files(theGen):
        print the_dir
        for the_file in files_in_dir:
            print ' -- ',the_file
    """
    dir_list = []
    last_dir = None
    for full_path in generator:
        (the_dir,the_file) = os.path.split( full_path )
        if the_dir != last_dir:
            dir_list.append( (the_dir, [the_file]) )
            last_dir = the_dir
        else:
            dir_list[len(dir_list)-1][1].append( the_file )
    return dir_list

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
