"""
Helper class that maintains the playback options information.

The object is set up to use the Python "with" syntax as follows:

    from maya.debug.PlaybackOptionsManager import PlaybackOptionsManager,PlaybackOptions

    with PlaybackOptionsManager() as mgr:
        mgr.setOption( 'minTime', 1.0 )
        mgr.setOption( 'maxTime', 10.0 )
        mgr.setOption( 'loop', 'once' )
        # Now you know for sure it will play exactly 10 frames, once,
        # regardless of what the user has for their playback options.
        cmds.play( wait=True )
    # And now the user's options are restored

That will ensure the original states are all restored when the
scope completes. There's no other reliable way to do it in Python.
If you need different syntax you can manually call the method to
complete the sequence:

    mgr = PlaybackOptionsManager()
    mgr.setOption( 'minTime', 1.0 )
    mgr.restore()

The first setOption() parameter corresponds to the names of the
parameters of the playbackOptions command:

    cmds.playbackOptions( minTime=... ) => setOption('minTime',...)
"""
import maya.cmds as cmds

__all__ = ['PlaybackOptionsManager', 'PlaybackOptions']

# Set this to true if you wish to see detailed information on exactly what the
# manager is enabling and disabling.
DEBUG_MODE = False

#======================================================================
def _dbg(message):
    '''
    Print out a message if the debug mode is enabled, otherwise do nothing
    '''
    if DEBUG_MODE:
        print message

#======================================================================
class PlaybackOptions(object):
    """
    Helper class to hold and capture all of the playback options
    """
    # List of all available playback options
    ALL_OPTIONS = [ 'animationEndTime', 'animationStartTime',
                    'blockingAnim', 'by', 'loop',
                    'maxPlaybackSpeed', 'playbackSpeed',
                    'maxTime', 'minTime', 'view']
    def __init__(self):
        """
        On creation load in all of the current options. That's all
        this class does. They remember the playback state. The
        member names don't follow PEP8 standards so that they can
        follow the naming convention used in the playbackOptions
        command.
        """
        for option in PlaybackOptions.ALL_OPTIONS:
            setattr(self, option, cmds.playbackOptions( **{ 'query':True, option:True} ) )

    def set_options(self):
        '''Set the playback options to the values in this class'''
        try:
            for option in PlaybackOptions.ALL_OPTIONS:
                option_value = getattr(self,option)
                _dbg( 'RESTORE {} to {}'.format(option, option_value) )
                cmds.playbackOptions( **{ option:option_value } )
        except Exception, ex:
            print 'ERR: Setting options "{}"'.format(ex)

#======================================================================
class PlaybackOptionsManager(object):
    #----------------------------------------------------------------------
    def __enter__(self):
        _dbg( '*** PlaybackOptionsManager::__enter__' )
        return self
    #----------------------------------------------------------------------
    def __init__(self):
        '''Defining both __enter__ and __init__ so that either one can be used'''
        _dbg( '*** PlaybackOptionsManager::__init__' )
        self.original_options = PlaybackOptions()

    #----------------------------------------------------------------------
    def __exit__(self,type,value,traceback):
        '''Ensure the state is restored if this object goes out of scope'''
        _dbg( '*** PlaybackOptionsManager::__exit__' )
        _dbg( '    Type = %s' % str(type) )
        _dbg( '    Value = %s' % str(value) )
        _dbg( '    Traceback = %s' % str(traceback) )
        self.restore()

    #----------------------------------------------------------------------
    @staticmethod
    def setOption(option, new_value):
        '''
        Method that modifies each of the playback options. The valid options
        come from the class member ALL_OPTIONS.
        '''
        _dbg( 'SET {} to {}'.format(option, new_value) )
        cmds.playbackOptions( **{ option:new_value } )

    #----------------------------------------------------------------------
    def restore(self):
        '''
        Restore the playback options to their original values prior to entering
        this one.  Not necessary to call this when using the "with PlaybackOptionsManager()"
        syntax. Only needed when you explicitly instantiate the options manager.
        Then you have to call this if you want your original state restored.
        '''
        _dbg( '*** PlaybackOptionsManager::restore' )

        self.original_options.set_options()

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
