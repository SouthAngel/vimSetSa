"""
Module containing the class responsible for getting names of plugs, nodes,
and DAG paths in a potentially unique and anonymous way.
"""
import os
import re
import math

__all__ = [ 'ObjectNamer' ]

class ObjectNamer(object):
    """
    Utility object to remap object names onto something appropriate.
    The simplest mapping is to return the name itself. If that's all
    you are ever going to do then don't use this class.

    The main use for this class is to anonymize names that might be
    considered sensitive. The anonymizing mode will ensure that the
    real name always matches the same generated name, and will give
    some minimal information within the name itself. (e.g. a file
    name will be called file_001, a directory name might be called
    dir_031, and a Maya transform node could be called transform_042.

    If you know how many objects you will be naming you can call
    ObjectNamer.set_max_objects(). This will guarantee that the formatting
    of the anonymized names can be lexically sorted correctly by using
    a zero-padded integer numbering system. This is useful because
    "file02" comes before "file10" but "file2" comes after it.

    The following anonymizer modes are supported:

        ObjectNamer( ObjectNamer.MODE_NAME )
            Names have no specific type. The are anonymized generically
                MySecretObject -> name01
        ObjectNamer( ObjectNamer.MODE_PLUG )
            Names are assumed to be Maya plug names. The node name part is
            anonymized but the attribute name is left as-is.
                MySecretNode.translateX -> node001.translateX
        ObjectNamer( ObjectNamer.MODE_NODE )
            Names are assumed to be Maya node names. The node name part is
            anonymized using the node type as a root if this module is
            executed inside of Maya, otherwise the generic 'node' is used.
                In Maya:    MySecretTransform -> transform001
                Standalone: MySecretTransform -> node001
        ObjectNamer( ObjectNamer.MODE_PATH )
            Names are assumed to be file paths. The first sections of the path
            are anonymized as directories, the final one is anonymized as a
            file. Paths with trailing separators (e.g. "/") are assumed to be
            directories. Paths are made into canonical form so all backslashes
            are replaced by forward slashes on Windows.
                root/parent/child/MySecretFile.ma -> dir1/dir2/dir3/file1.ma
                root/parent/child/MySecretDir/    -> dir1/dir2/dir3/dir4/

    Class members:
        name_type        : Naming method to use (MODE_NAME, MODE_PLUG, MODE_NODE, MODE_PATH)
        anonymous        : If True all names will be anonnymized, else used as-is
        maya_cmds        : If Maya commands are available they can be accessed through this
        name_fmt         : Formatting string for anonymous names - includes the proper
                           number of expected leading zeroes based on max object count
        anonymized_names : Directory of already assigned anonymous names (ORIGINAL : ANONYMOUS_NAME)
        unique_id        : Directory of unique IDs to use for anonymizing.
                          Key is the type of object, value is the next unique ID for it.

        Usage:
            import ObjectNamer
            oNamer = ObjectNamer.ObjectNamer( ObjectNamer.MODE_NAME, anonymous=True )
            oNamer.set_max_objects( 100 )
            print oNamer.name( "My Funky Thing" )
            # Result = "name_01"
            print oNamer.name( "Some Other Stuff" )
            # Result = "name_02"
            print oNamer.name( "My Funky Thing" )
            # Result = "name_01"
            noNamer = ObjectNamer.ObjectNamer( ObjectNamer.MODE_NAME, anonymous=False )
            print oNamer.name( "My Funky Thing" )
            # Result = "My Funky Thing"
    """
    MODE_NAME = 0   # Rename simple strings. Everything is called "name_#"
    MODE_PLUG = 1   # Rename Maya plugs. The node name is anonymous, the attribute is not
    MODE_NODE = 2   # Rename Maya nodes. If Maya is present then it is used to
                    #    get node type names as the unique prefix such as
                    #    "transform_#" and "mesh_#". Otherwise the generic
                    #    names "node_#" are generated.
    MODE_PATH = 3   # Rename file paths. Directories and file names are
                    #    anonymized separately to something like "dir_1/dir_2/file_1"

    SEP_DRIVE       = r':'    # Separator between drive name and path on Windows
    SEP_NAMESPACE   = r':'    # Separator between namespace and the rest of the node
    SEP_NODE        = r'\|'   # Separator between nodes at each level of the DAG
    SEP_UNDERWORLD  = r'->'   # Separator between shape node and underworld
    SEP_ATTRIBUTE   = r'\.'   # Separator between node name and attribute name in plug
    SEP_PATH        = r'/'    # Separator between path directory elements

    NAME_DIRECTORY  = 'dir'         # Generic name for a directory along a file path
    NAME_FILE       = 'file'        # Generic name for the leaf of a file path
    NAME_GENERIC    = 'name'        # Generic name for generic object
    NAME_NODE       = 'node'        # Generic name for node component of a path
    NAME_NAMESPACE  = 'namespace'   # Generic name for namespace component of a path
    NAME_UNDERWORLD = 'underworld'  # Generic name for underworld component of a path

    #======================================================================
    def __init__(self, name_type, anonymous):
        """
        Create a namer.
            name_type:  NODE_{NAME,PLUG,NODE,PATH}
            anonymous: True means don't use the original names, anonymize them
        """
        self.name_type = name_type
        self.anonymous = anonymous
        self.name_fmt = None
        self.anonymized_names = {}
        self.unique_id = {}
        # Check the two most common usages for importing Maya commands
        if 'maya.cmds' in globals():
            self.maya_cmds = globals()['maya.cmds']
        elif 'cmds' in globals():
            self.maya_cmds = globals()['cmds']
        else:
            self.maya_cmds = None

        self.clear()

    #======================================================================
    def clear(self):
        """
        Erase all of the currently remembered names. Resets the unique IDs
        back to the original. Names generated after a clear() may not be
        unique compared to names generated before the clear().
        """
        self.name_fmt = '%s_%d'
        self.anonymized_names = {}

        # Why use a dictionary here you ask? To make names more friendly.
        # When naming anonymous node types in Maya we want to increment
        # separate counters for each type. That way instead of this:
        #
        #    someTransform      => transform_1
        #    someOtherTransform => transform_2
        #    someCamera         => camera_3
        #
        # we get this:
        #
        #    someTransform      => transform_1
        #    someOtherTransform => transform_2
        #    someCamera         => camera_1
        #
        self.unique_id = {}

    #======================================================================
    def set_max_objects(self, max_objects):
        """
        Set the maximum number of objects expected to be named with this
        namer. This allows creation of a consistent number of leading
        zeroes on anonymized ID values for easy sorting.

        If max_objects is 0 then use the %d format with no leading zeroes.
        """
        if max_objects <= 10:
            self.name_fmt = '%s_%d'
        else:
            self.name_fmt = '%%s_%%0%dd' % int(math.log(max_objects-1,10)+1)

    #======================================================================
    def name(self, original_name):
        """
        Get the name which corresponds to "original_name". In the case of
        non-anonymized names that will just be the original name.
        """
        mapped_name = original_name
        # Only alter the name if the anonymizer is enabled
        if self.anonymous:
            # If the name has already been anonymized used the same altered version
            if original_name in self.anonymized_names:
                return self.anonymized_names[original_name]

            if self.name_type == ObjectNamer.MODE_NAME:
                return self.__anonymized_name( original_name )

            if self.name_type == ObjectNamer.MODE_PLUG:
                return self.__anonymized_plug( original_name )

            if self.name_type == ObjectNamer.MODE_NODE:
                return self.__anonymized_node( original_name )

            if self.name_type == ObjectNamer.MODE_PATH:
                return self.__anonymized_path( original_name )

            raise NameError('Unrecognized naming type: %d' % self.name_type)

        return mapped_name

    #======================================================================
    def __next_unique_id(self, forThisType):
        """
        Get the next available unique ID for the given type of object.
        """
        self.unique_id[forThisType] = self.unique_id.get(forThisType, -1) + 1
        return self.unique_id[forThisType]

    #======================================================================
    def __anonymized_name(self, original_name):
        """
        Return an anonymized version of the given name. Uses a base
        name of "name" and a unique ID with the appropriate number of
        digits.
        """
        mapped_name = self.__unique_name( ObjectNamer.NAME_GENERIC )
        self.anonymized_names[original_name] = mapped_name
        return mapped_name

    #======================================================================
    def __anonymized_plug(self, original_name):
        """
        Return an anonymized version of the given plug name. When Maya is
        present the node portion of the name is anonymized with the type
        of node, otherwise the generic string "node" is used. The attribute
        portion is not anonymized.

        No attempt is made to ensure that the plug string itself is valid.
        """
        if original_name in self.anonymized_names:
            return self.anonymized_names[original_name]

        try:
            (node,attribute) = re.split(ObjectNamer.SEP_ATTRIBUTE, original_name, 1)
        except ValueError:
            node = original_name
            attribute = None

        # I can use this as well since plug names and node names won't overlap
        # so the namespaces will not corrupt each other
        mapped_name = self.__anonymized_node( node )

        if attribute:
            # Avoid the '\' escape character for the prefix of SEP_ATTRIBUTE
            mapped_name = '%s%s%s' % (mapped_name, ObjectNamer.SEP_ATTRIBUTE[1], attribute)

        self.anonymized_names[original_name] = mapped_name

        return mapped_name

    #======================================================================
    def __unique_name(self, name_type):
        """
        Get a unique generic name of the specified type.
        """
        return self.name_fmt % (name_type, self.__next_unique_id(name_type))

    #======================================================================
    def __anonymized_node(self, original_name):
        """
        Return an anonymized version of the given node name. When Maya is
        present the node portion of the name is anonymized with the type
        of node, otherwise the generic string "node" is used.

        No attempt is made to ensure that the node string is valid.

        Like file paths the node paths could have partial matches so they
        are all checked along the way. (e.g. the two instances a|b|c1
        and a|b|c2 should both map their a|b portion to the same thing)

        Node format broken out is:
            [NAMESPACE:]*                    Optional
                NODENAME                    Mandatory
                    [|NODENAME]*            Optional
                        {->[UNDERWORLD]}    Optional
        """
        if original_name in self.anonymized_names:
            return self.anonymized_names[original_name]

        #    [NAMESPACE:]*                    Optional
        namespaces = re.split(ObjectNamer.SEP_NAMESPACE, original_name)
        if len(namespaces) == 1:
            namespaces = []
            node_path = original_name
        else:
            node_path = namespaces[-1]
            namespaces = namespaces[:-1]

        #    [|NODENAME]*            Optional
        instances = re.split(ObjectNamer.SEP_NODE, node_path)
        if len(instances) == 1:
            instances = []
        else:
            node_path = instances[-1]
            instances = instances[:-1]

        #    {->[UNDERWORLD]}    Optional
        underworlds = re.split(ObjectNamer.SEP_UNDERWORLD, node_path)
        if len(underworlds) == 1:
            underworld = None
        else:
            # Treat the underworld as atomic, otherwise we could get into a big
            # mess of recursive checking
            node_path = underworlds[0]
            underworld = ObjectNamer.SEP_UNDERWORLD.join(underworlds[1:])

        # Now that we've torn the name apart we can build it back up again,
        # piece by piece.
        mapped_name = ''
        unmapped_name = ''
        for namespace in namespaces:
            unmapped_name += '%s%s' % (namespace, ObjectNamer.SEP_NAMESPACE)
            if unmapped_name in self.anonymized_names:
                mapped_name = self.anonymized_names[unmapped_name]
            else:
                mapped_name += self.__unique_name(ObjectNamer.NAME_NAMESPACE)
                mapped_name += ObjectNamer.SEP_NAMESPACE
                self.anonymized_names[unmapped_name] = mapped_name

        # Add any instances or full path elements along the way
        prefix = ''
        for instance in instances:
            unmapped_name += prefix + instance
            if unmapped_name in self.anonymized_names:
                mapped_name = self.anonymized_names[unmapped_name]
            else:
                if self.maya_cmds is not None:
                    nodeType = self.maya_cmds.nodeType(unmapped_name)
                else:
                    nodeType = ObjectNamer.NAME_NODE
                mapped_name += prefix + self.__unique_name( nodeType )
                self.anonymized_names[unmapped_name] = mapped_name
            prefix = ObjectNamer.SEP_NODE[1]    # Avoid the '\' escape character for the prefix

        # Now the leaf node name
        unmapped_name += prefix + node_path
        if unmapped_name in self.anonymized_names:
            mapped_name = self.anonymized_names[unmapped_name]
        else:
            if self.maya_cmds is not None:
                nodeType = self.maya_cmds.nodeType(unmapped_name)
            else:
                nodeType = ObjectNamer.NAME_NODE
            mapped_name += prefix + self.__unique_name(nodeType)
            self.anonymized_names[unmapped_name] = mapped_name

        # And finally the underworld, if it exists
        if underworld:
            unmapped_name += ObjectNamer.SEP_UNDERWORLD + underworld
            if unmapped_name in self.anonymized_names:
                mapped_name = self.anonymized_names[unmapped_name]
            else:
                mapped_name += ObjectNamer.SEP_UNDERWORLD
                mapped_name += self.__unique_name(ObjectNamer.NAME_UNDERWORLD)
                self.anonymized_names[unmapped_name] = mapped_name

        return mapped_name

    #======================================================================
    def __anonymized_path(self, original_name):
        """
        Return an anonymized version of the given file path. If the last
        element of the path ends in a '/' or '\' then the path is assumed
        to be a directory, otherwise it is assumed to be a path.

        The following replacements are made to the original name:
            '\' are all replaced by '/', for consistency
            Leading Windows disk names "X:" are replaced by the absolute
                path beginning "/X"
            Directories in the path are replaced with 'dir_#'
                # is taken from the unique directory ID
            The file in the path, if any, is replaced with 'file_#'
                # is taken from the unique file ID

        The directory anonymizer is tricky because it has to check for
        mapped directories from the top down. i.e. "/a/b/c" should remap
        all of "/a", "/a/b", and "/a/b/c".
        """
        original_name.replace( os.sep, ObjectNamer.SEP_PATH )
        (path,the_file) = os.path.split( original_name )
        # Catch the special case of terminating "/", e.g. ".../path/"
        if the_file == '':
            path += ObjectNamer.SEP_PATH
            the_file = None
        parts = re.split(ObjectNamer.SEP_DRIVE, path)
        built_path = ''
        if len(parts) > 1:
            built_path = '%s%s' % (parts[0], ObjectNamer.SEP_DRIVE)
            dirs = re.split(ObjectNamer.SEP_PATH, parts[1])
        else:
            dirs = re.split(ObjectNamer.SEP_PATH, parts[0])
            if dirs[0] == '':
                if len(dirs) > 1:
                    built_path = ObjectNamer.SEP_PATH
                    dirs = dirs[1:]
                else:
                    dirs = []
            elif len(dirs) == 0:
                built_path = ''
                dirs = []

        # Build up the directory a level at a time so that any subdirectory
        # that is already mapped will be used.
        for theDir in range(0,len(dirs)):
            dirElement = dirs[theDir]
            if theDir > 0:
                built_path += ObjectNamer.SEP_PATH
            # This catches a directory with a trailing '/'
            if dirElement == '':
                continue
            temp_path = built_path + dirElement
            # If the partial path exists then switch over to its
            # anonymized name
            if temp_path in self.anonymized_names:
                built_path = self.anonymized_names[temp_path]
            else:
                built_path += self.__unique_name(ObjectNamer.NAME_DIRECTORY)
                self.anonymized_names[temp_path] = built_path

        # Lastly if there is a file component append that onto the end
        if the_file:
            if built_path != '':
                built_path += ObjectNamer.SEP_PATH
            temp_path = built_path + the_file
            if temp_path in self.anonymized_names:
                built_path = self.anonymized_names[temp_path]
            else:
                built_path  += self.__unique_name(ObjectNamer.NAME_FILE)

        self.anonymized_names[original_name] = built_path

        return built_path

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
