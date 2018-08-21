
import maya.cmds
import sys, os.path

# Locations of commandList file by OS type as returned by maya.cmds.about( os=True )
commandListLocations = {
    'nt' : 'bin',
    'win64' : 'bin',
    'mac' : 'Resources',
    'linux' : 'lib',
    'linux64' : 'lib'
}

def __makeStubFunc( command, library ):
    def stubFunc( *args, **keywords ):
        """ Dynamic library stub function """
        maya.cmds.dynamicLoad( library )
        # call the real function which has replaced us
        return maya.cmds.__dict__[command]( *args, **keywords )
    return stubFunc

def processCommandList():
    """
    Process the "commandList" file that contains the mappings between command names and the
    libraries in which they are found.  This function will install stub functions in maya.cmds
    for all commands that are not yet loaded.  The stub functions will load the required library
    and then execute the command.
    """

    try:
        # Assume that maya.cmds.about and maya.cmds.internalVar are already registered
        #
        commandListPath = os.path.realpath( os.environ[ 'MAYA_LOCATION' ] )
        platform = maya.cmds.about( os=True )
        commandListPath = os.path.join( commandListPath, commandListLocations[platform], 'commandList' )

        file = open( commandListPath, 'r' )
        for line in file:
            commandName, library = line.split()
            if not commandName in maya.cmds.__dict__:
                maya.cmds.__dict__[commandName] = __makeStubFunc( commandName, library )
    except:
        sys.stderr.write("Unable to process commandList %s" % commandListPath)
        raise

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
