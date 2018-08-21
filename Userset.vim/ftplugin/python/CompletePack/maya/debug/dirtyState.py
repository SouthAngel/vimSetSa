"""
Utility to read and analyze dependency graph dirty state information.
Allows you to produce a comparision of two sets of state information.

    from dirtyState import *

    # Get the current scene's dirty data state information
    stateBefore = dirtyState( check_data=True )

    # Perform some operation that may change the dirty state
    doMyOperation()

    # Get the new dirty data state information
    stateAfter = dirtyState( check_data=True )

    # Compare them to see if they are the same
    stateBefore.compare(stateAfter)
"""

__all__ = ['dirtyState']

import re
import sys

#======================================================================
#
# State analysis of offline files will work without Maya running so use
# the maya import to dynamically detect what can and can't be done here.
#
try:
    import maya.cmds as cmds
    MAYA_IS_AVAILABLE = True
except Exception:
    MAYA_IS_AVAILABLE = False
def checkMaya():
    """
    Returns True if this script is running from inside Maya, which it
    needs to be in order to work.
    """
    if MAYA_IS_AVAILABLE:
        return True
    print 'ERROR: Cannot perform this operation unless Maya is available'
    return False

#######################################################################

class dirtyState(object):
    """
    Provides access and manipulation of dirty state data that has been
    produced by various invocations of the 'dgdirty' command.
    """

    # Keywords used for commands and output formatting
    PLUG_TYPE = 'plug'
    DATA_TYPE = 'data'
    CONNECTION_TYPE = 'connection'
    CLEAN_TYPE = 'clean'
    DIRTY_TYPE = 'dirty'

    # Precompile the line expressions for faster matching
    RE_CONNECTION = re.compile(r'\s*connection\s*([^\t]+)\t([^\s]+)\s*$')
    RE_PLUG = re.compile(r'\s*plug\s*([^\s]+)\s*$')
    RE_DATA = re.compile(r'\s*data\s*([^\s]+)\s*$')

    #======================================================================
    def __init__(self,
                 state_file_name=None,
                 long_names=False,
                 check_plugs=True,
                 check_data=True,
                 check_connections=True):
        """
        Create a dirty state object from a file or the current scene.

        The dirty data is read in and stored internally in a format that makes
        formatting and comparison easy.

            name              : Name of the state object's data (e.g. file name)
            state_file_name   : If None then the current scene will be used,
                                otherwise the file will be read.
            long_names        : If True then don't attempt to shorten the node
                                names by removing namespaces and DAG path elements.
            check_plugs       : If True then check for plugs that are dirty
            check_data        : If True then check for plug data that is dirty
            check_connections : If True then check for connections that are dirty

        This is generated data, not to be used externally:
            _plugs[]       : List of plugs that are dirty
            _data[]        : List of data values that are dirty
            _connections[] : List of connections that are dirty
        """
        self.use_long_names = long_names
        self.check_plugs = check_plugs
        self.check_data = check_data
        self.check_connections = check_connections
        self.name = None
        self.plugs = []
        self.data = []
        self.connections = []

        if state_file_name == None:
            self._init_from_scene()
        else:
            self._init_from_file(state_file_name)

    #======================================================================
    def _init_from_scene(self):
        """
        Create a dirty state object from the selected objects in the current
        Maya scene. If nothing is selected then create the state object from
        all plugs in the scene (as determined by the dgdirty "allPlugs" flag).
        """
        if not checkMaya():
            return

        # If nothing is currently selected then read all plugs
        selected_plugs = cmds.ls(selection=True)
        list_all_plugs = selected_plugs is None or not selected_plugs

        self.name = '__SCENE__'
        self.plugs = []
        self.data = []
        self.connections = []

        if self.check_plugs:
            plug_list = cmds.dgdirty( allPlugs=list_all_plugs, list=dirtyState.PLUG_TYPE )
            if plug_list:
                self.plugs = plug_list

        if self.check_data:
            dataList = cmds.dgdirty( allPlugs=list_all_plugs, list=dirtyState.DATA_TYPE )
            if dataList:
                self.data = dataList

        if self.check_connections:
            connection_list = cmds.dgdirty( allPlugs=list_all_plugs, list=dirtyState.CONNECTION_TYPE )
            if connection_list:
                for connection in range(0,len(connection_list),2):
                    self.connections.append( (connection_list[connection], connection_list[connection+1]) )

    #======================================================================
    def _init_from_file(self, state_file_name):
        """
        Create a dirty state object from contents of the given file.
        Data in the file will be lines showing what is dirty:

            connection<tab>X<tab>Y    : The connection from X to Y is dirty
            plug<tab>X                : Networked plug X is dirty
            data<tab>X                : Plug X has dirty data in the datablock
        """
        self.name = state_file_name
        self.plugs = []
        self.data = []
        self.connections = []

        state_file = open(state_file_name, 'r')
        for line in state_file:
            match = dirtyState.RE_CONNECTION.match( line )
            if match:
                self.connections.append( (match.group(1), match.group(2)) )
                continue

            match = dirtyState.RE_PLUG.match( line )
            if match:
                self.plugs.append( match.group(1) )
                continue

            match = dirtyState.RE_DATA.match( line )
            if match:
                self.data.append( match.group(1) )
                continue

            if len(line.rstrip().lstrip()) > 0: # Allow blank lines
                print 'WARN: Line not recognized: %s' % line,

    #======================================================================
    def write(self, fileName=None):
        """
        Dump the states in the .dirty format it uses for reading. Useful for
        creating a dump file from the current scene, or just viewing the
        dirty state generated from the current scene. If the fileName is
        specified then the output is sent to that file, otherwise it goes
        to stdout.
        """
        out = sys.stdout
        if fileName:
            out = open(fileName, 'w')

        for data in self.data:
            out.write( '%s\t%s\n' % (dirtyState.DATA_TYPE, data) )

        for plug in self.plugs:
            out.write( '%s\t%s\n' % (dirtyState.PLUG_TYPE, plug) )

        for (src,dst) in self.connections:
            out.write( '%s\t%s\t%s\n' % (dirtyState.CONNECTION_TYPE, src, dst) )

    #======================================================================
    def _get_plug_differences(self, other, made_dirty):
        """
        Compare this dirty state against another one and generate a
        summary of plugs whose dirty state changed:

            made_dirty    : If true return plugs dirty in other but not in self
                          If false return plugs dirty in self but not in other
        """
        differences = []

        if made_dirty:
            for plug in other.plugs:
                if plug in self.plugs:
                    continue
                differences.append( plug )
        else:
            for plug in self.plugs:
                if plug in other.plugs:
                    continue
                differences.append( plug )

        return differences

    #======================================================================
    def _get_data_differences(self, other, made_dirty):
        """
        Compare this dirty state against another one and generate a
        summary of data whose dirty state changed:

            made_dirty    : If true return data dirty in other but not in self
                          If false return data dirty in self but not in other
        """
        differences = []

        if made_dirty:
            for data in other.data:
                if data in self.data:
                    continue
                differences.append( data )
        else:
            for data in self.data:
                if data in other.data:
                    continue
                differences.append( data )

        return differences

    #======================================================================
    def _get_connection_differences(self, other, made_dirty):
        """
        Compare this dirty state against another one and generate a
        summary of connections whose dirty state changed:

            made_dirty    : If true return connections dirty in other but not in self
                          If false return connections dirty in self but not in other
        """
        differences = []

        if made_dirty:
            for connection in other.connections:
                if connection in self.connections:
                    continue
                differences.append( connection )
        else:
            for connection in self.connections:
                if connection in other.connections:
                    continue
                differences.append( connection )

        return differences

    #======================================================================
    def compare(self, other):
        """
        Compare this dirty state against another one and generate a
        summary of how the two sets differ. Differences will be returned
        as a string list consisting of difference descriptions. That way
        when testing, an empty return means the graphs are the same.

        The difference type formats are:

            plug dirty N            Plug was dirty in other but not in self
            plug clean N            Plug was dirty in self but not in other
            data dirty N            Data was dirty in other but not in self
            data clean N            Data was dirty in self but not in other
            connection dirty S D    Connection was dirty in other but not in self
            connection clean S D    Connection was dirty in self but not in other
        """
        differences = []

        differences += ['%s %s %s' % (dirtyState.PLUG_TYPE, dirtyState.DIRTY_TYPE, plug)
                        for plug in self._get_plug_differences(other, True)]
        differences += ['%s %s %s' % (dirtyState.PLUG_TYPE, dirtyState.CLEAN_TYPE, plug)
                        for plug in self._get_plug_differences(other, False)]

        differences += ['%s %s %s' % (dirtyState.DATA_TYPE, dirtyState.DIRTY_TYPE, data)
                        for data in self._get_data_differences(other, True)]
        differences += ['%s %s %s' % (dirtyState.DATA_TYPE, dirtyState.CLEAN_TYPE, data)
                        for data in self._get_data_differences(other, False)]

        differences += ['%s %s %s %s' % (dirtyState.CONNECTION_TYPE, dirtyState.DIRTY_TYPE, connection[0], connection[1])
                        for connection in self._get_connection_differences(other, True)]
        differences += ['%s %s %s %s' % (dirtyState.CONNECTION_TYPE, dirtyState.CLEAN_TYPE, connection[0], connection[1])
                        for connection in self._get_connection_differences(other, False)]

        return differences

    #======================================================================
    def compare_one_type(self, other, request_type, made_dirty):
        """
        Compare this dirty state against another one and return the values
        that differ in the way proscribed by the parameters:

            request_type    : Type of dirty state to check [plug/data/connection]
            made_dirty    : If true return things that became dirty, otherwise
                          return things that became clean

        Nothing is returned for items that did not change.
        """
        differences = []

        if request_type == dirtyState.PLUG_TYPE:
            differences = self._get_plug_differences( other, made_dirty )

        #----------------------------------------

        elif request_type == dirtyState.DATA_TYPE:
            differences = self._get_data_differences( other, made_dirty )

        #----------------------------------------

        elif request_type == dirtyState.CONNECTION_TYPE:
            differences = self._get_connection_differences( other, made_dirty )

        return differences

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
