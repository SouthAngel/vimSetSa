"""
Holds the helper class playbackModeManager used to change and restore
the playbackOptions within a scope. Load with:

        from maya.debug.playbackModeManager import playbackModeManager
"""
import maya.cmds as cmds

__all__ = ['playbackModeManager']

# Set this to true if you wish to see detailed information on exactly what the
# manager is enabling and disabling.
DEBUG_MODE = False

#======================================================================
def _dbg(message):
    '''Print the message if in debug mode'''
    if DEBUG_MODE:
        print message

#======================================================================
class playbackModeManager(object):
    '''
    Helper class that maintains the playback mode information.

    It maintains state information for all playback options so that they can be
    modified within a scope and have the original settings restored on completion.

    Calling any of the setXXX() methods

    The object is set up to use the Python "with" syntax as follows:

        with playbackModeManager() as mgr:
            mgr.setOptions( minTime=newStartFrame )

    That will ensure the original states are all restored. There's no other
    reliable way to do it in Python. If you need different scoping that can't
    be put into a nice code block like this you can manually call the methods
    to complete the sequence:

        mgr = playbackModeManager()
            ...
        mgr.setOptions( minTime=newStartFrame )
            ...
        mgr.restore()

    You may also be interested in this utility method that will playback the
    entire range from the start in 'wait' mode. Two reasons you want this:
        1. If you don't play in 'wait' mode then your manager can go out of
           scope while playback is running.
        2. Playing in 'wait' mode starts from the current frame and it does
           not rewind if you're already at the end.

        ...
        mgr.playAll()
        ...
    '''
    #----------------------------------------------------------------------
    def __enter__(self):
        '''Beginning of scope object for "with" statement. __init__ does all intialization'''
        _dbg( '*** playbackModeManager::__enter__' )
        return self

    #----------------------------------------------------------------------
    def __init__(self):
        '''Defining both __enter__ and __init__ so that either one can be used'''
        _dbg( '*** playbackModeManager::__init__' )

        self.animationEndTime = cmds.playbackOptions( query=True, animationEndTime=True )
        _dbg( 'Save animationEndTime = {}'.format(self.animationEndTime) )

        self.animationStartTime = cmds.playbackOptions( query=True, animationStartTime=True )
        _dbg( 'Save animationStartTime = {}'.format(self.animationStartTime) )

        self.blockingAnim = cmds.playbackOptions( query=True, blockingAnim=True )
        _dbg( 'Save blockingAnim = {}'.format(self.blockingAnim) )

        self.currentTime = cmds.currentTime( query=True )
        _dbg( 'Current time = {}'.format( self.currentTime ) )

        self.by = cmds.playbackOptions( query=True, by=True )
        _dbg( 'Save by = {}'.format(self.by) )

        self.framesPerSecond = cmds.playbackOptions( query=True, framesPerSecond=True )
        _dbg( 'Save framesPerSecond = {}'.format(self.framesPerSecond) )

        self.loop = cmds.playbackOptions( query=True, loop=True )
        _dbg( 'Save loop = {}'.format(self.loop) )

        self.maxPlaybackSpeed = cmds.playbackOptions( query=True, maxPlaybackSpeed=True )
        _dbg( 'Save maxPlaybackSpeed = {}'.format(self.maxPlaybackSpeed) )

        self.maxTime = cmds.playbackOptions( query=True, maxTime=True )
        _dbg( 'Save maxTime = {}'.format(self.maxTime) )

        self.minTime = cmds.playbackOptions( query=True, minTime=True )
        _dbg( 'Save minTime = {}'.format(self.minTime) )

        self.playbackSpeed = cmds.playbackOptions( query=True, playbackSpeed=True )
        _dbg( 'Save playbackSpeed = {}'.format(self.playbackSpeed) )

        self.view = cmds.playbackOptions( query=True, view=True )
        _dbg( 'Save view = {}'.format(self.view) )

        self.needsRestoring = False

    #----------------------------------------------------------------------
    def __exit__(self,theType,theValue,traceback):
        '''Ensure the state is restored if this object goes out of scope'''
        _dbg( '*** playbackModeManager::__exit__' )
        _dbg( '    Type      = {}'.format(theType) )
        _dbg( '    Value     = {}'.format(theValue) )
        _dbg( '    Traceback = {}'.format(traceback) )
        self.restore()

    #----------------------------------------------------------------------
    @staticmethod
    def playAll():
        '''Playback the entire animation sequence, returning the elapsed time when it is done'''
        _dbg( '*** playbackModeManager::playAll' )
        cmds.currentTime( cmds.playbackOptions(query=True,minTime=True) )
        start_time = cmds.timerX()
        cmds.play( wait=True )
        elapsed_time = cmds.timerX(startTime=start_time)

        if cmds.currentTime(query=True) != cmds.playbackOptions(query=True,maxTime=True):
            _dbg( '### ERR: Play All to {} ended on frame {}'.format(cmds.playbackOptions(query=True,maxTime=True), cmds.currentTime(query=True)) )

        return elapsed_time

    #----------------------------------------------------------------------
    def playRange(self, minTime, maxTime):
        '''
        Playback the given animation range, returning the elapsed time when it is done.
        The time range is only set temporarily for this playback sequence.
        If you wish to permanently change the time range use setOptions().
        '''
        _dbg( '*** playbackModeManager::playRange(%d,%d)' % (minTime,maxTime) )
        original_min_time = cmds.playbackOptions( query=True, minTime=True )
        original_max_time = cmds.playbackOptions( query=True, maxTime=True )
        self.setOptions( minTime=minTime, maxTime=maxTime )

        cmds.currentTime( minTime )
        start_time = cmds.timerX()
        cmds.play( wait=True )
        elapsed_time = cmds.timerX(startTime=start_time)

        self.setOptions( minTime=original_min_time, maxTime=original_max_time )
        if cmds.currentTime(query=True) != maxTime:
            _dbg( '### ERR: Playrange {} - {} ended on frame {}'.format(minTime, maxTime, cmds.currentTime(query=True)) )
        return elapsed_time

    #----------------------------------------------------------------------
    def setLimitedRange(self, maxFrames, fromStart=False):
        '''
        Set up the manager to play the given animation range by setting the
        minTime and maxTime to respect the arguments. After calling this you
        can use playAll() rather than playRange() or playLimitedRange().

        The time range is set for the duration of this manager so only use
        it if you will be using the same range repeatedly. It returns a
        tuple of (original_min_time, original_max_time) in case you want
        to restore it later.

        maxFrames: Maximum number of frames to play
        fromStart: When set to True this will first move the playback to the first
                   frame of the animation. Otherwise it will go to what the current
                   time was when the manager was created. This allows you to get
                   consistent limited length playbacks from an arbitrary starting
                   frame.

        Note: If the current time is at or near the maxTime and you do not
              specify 'fromStart=True' there may be little or no animation so
              make sure your scene is set up appropriate if you use that option.
        '''
        _dbg( '*** playbackModeManager::setLimitedRange(%d)' % (maxFrames) )
        original_min_time = self.minTime
        original_max_time = self.maxTime

        minTime = self.minTime if fromStart else self.currentTime
        maxTime = self.maxTime
        if self.maxTime - minTime >= maxFrames:
            # If the range is too large then stop early
            maxTime = minTime + maxFrames - 1

        self.setOptions( minTime=minTime, maxTime=maxTime )

        return (original_min_time, original_max_time)

    #----------------------------------------------------------------------
    def playLimitedRange(self, maxFrames, fromStart=False):
        '''
        Playback the given animation range, returning the elapsed time when it is done.
        The time range is only set temporarily for this playback sequence.
        If you wish to permanently change the time range use setOptions().

        maxFrames: Maximum number of frames to play
        fromStart: When set to True this will first move the playback to the first
                   frame of the animation. Otherwise it will go to what the current
                   time was when the manager was created. This allows you to get
                   consistent limited length playbacks from an arbitrary starting
                   frame.

        Note: If the current time is at or near the maxTime and you do not
              specify 'fromStart=True' there may be little or no animation so
              make sure your scene is set up appropriate if you use that option.
        '''
        _dbg( '*** playbackModeManager::playLimitedRange(%d)' % (maxFrames) )
        minTime = self.minTime if fromStart else self.currentTime
        maxTime = self.maxTime
        if self.maxTime - minTime >= maxFrames:
            # If the range is too large then stop early
            maxTime = minTime + maxFrames - 1
        return self.playRange( minTime, maxTime )

    #----------------------------------------------------------------------
    def setOptions(self
                 , animationEndTime=None
                 , animationStartTime=None
                 , blockingAnim=None
                 , byValue=None
                 , framesPerSecond=None
                 , loop=None
                 , maxPlaybackSpeed=None
                 , maxTime=None
                 , minTime=None
                 , playbackSpeed=None
                 , view=None
                 ):
        '''
        Mirror the arguments used by the playbackOptions command. A value of
        "None" means "don't set this particular value".

        raises ValueError if the playbackOption command failed.
        '''
        try:
            if None != animationEndTime:
                _dbg( 'Set animationEndTime = {}'.format(animationEndTime) )
                cmds.playbackOptions( animationEndTime=animationEndTime )

            if None != animationStartTime:
                _dbg( 'Set animationStartTime = {}'.format(animationStartTime) )
                cmds.playbackOptions( animationStartTime=animationStartTime )

            if None != blockingAnim:
                _dbg( 'Set blockingAnim = {}'.format(blockingAnim) )
                cmds.playbackOptions( blockingAnim=blockingAnim )

            if None != byValue:
                _dbg( 'Set by = {}'.format(byValue) )
                cmds.playbackOptions( by=byValue )

            if None != framesPerSecond:
                _dbg( 'Set framesPerSecond = {}'.format(framesPerSecond) )
                cmds.playbackOptions( framesPerSecond=framesPerSecond )

            if None != loop:
                _dbg( 'Set loop = {}'.format(loop) )
                cmds.playbackOptions( loop=loop )

            if None != maxPlaybackSpeed:
                _dbg( 'Set maxPlaybackSpeed = {}'.format(maxPlaybackSpeed) )
                cmds.playbackOptions( maxPlaybackSpeed=maxPlaybackSpeed )

            if None != maxTime:
                _dbg( 'Set maxTime = {}'.format(maxTime) )
                cmds.playbackOptions( maxTime=maxTime )

            if None != minTime:
                _dbg( 'Set minTime = {}'.format(minTime) )
                cmds.playbackOptions( minTime=minTime )

            if None != playbackSpeed:
                _dbg( 'Set playbackSpeed = {}'.format(playbackSpeed) )
                cmds.playbackOptions( playbackSpeed=playbackSpeed )

            if None != view:
                _dbg( 'Set view = {}'.format(view) )
                cmds.playbackOptions( view=view )

        except Exception, ex:
            raise ValueError('Found an invalid playback option value ({})'.format(ex))

        self.needsRestoring = True

    #----------------------------------------------------------------------
    def restore(self):
        '''
        Restore the playback options to their original values (i.e. the ones
        present when this object was constructed).

        It's necessary to call this when using the "with playbackModeManager()"
        syntax. It's only needed when you explicitly instantiate the mode manager.
        Then you have to call this if you want your original state restored,
        or wait for the unknown point in the future where this object is
        destroyed.
        '''
        _dbg( '*** playbackModeManager::restore' )
        # Prevent multiple calls
        if not self.needsRestoring:
            _dbg( '    Oops, nothing to restore' )
            return

        # The playbackOptions command can probably handle restoring multiple
        # options at once but why tempt fate. This way allows for easier
        # debugging should any of the individual option restores not work.
        #
        try:
            _dbg( 'Restore animationEndTime = {}'.format(self.animationEndTime) )
            cmds.playbackOptions( animationEndTime=self.animationEndTime )

            _dbg( 'Restore animationStartTime = {}'.format(self.animationStartTime) )
            cmds.playbackOptions( animationStartTime=self.animationStartTime )

            _dbg( 'Restore blockingAnim = {}'.format(self.blockingAnim) )
            cmds.playbackOptions( blockingAnim=self.blockingAnim )

            _dbg( 'Restore by = {}'.format(self.by) )
            cmds.playbackOptions( by=self.by )

            _dbg( 'Restore framesPerSecond = {}'.format(self.framesPerSecond) )
            cmds.playbackOptions( framesPerSecond=self.framesPerSecond )

            _dbg( 'Restore loop = {}'.format(self.loop) )
            cmds.playbackOptions( loop=self.loop )

            _dbg( 'Restore maxPlaybackSpeed = {}'.format(self.maxPlaybackSpeed) )
            cmds.playbackOptions( maxPlaybackSpeed=self.maxPlaybackSpeed )

            _dbg( 'Restore maxTime = {}'.format(self.maxTime) )
            cmds.playbackOptions( maxTime=self.maxTime )

            _dbg( 'Restore minTime = {}'.format(self.minTime) )
            cmds.playbackOptions( minTime=self.minTime )

            _dbg( 'Restore playbackSpeed = {}'.format(self.playbackSpeed) )
            cmds.playbackOptions( playbackSpeed=self.playbackSpeed )

            _dbg( 'Restore view = {}'.format(self.view) )
            cmds.playbackOptions( view=self.view )

            # Do not restore current if it is unchanged. It would trigger an unwanted evaluation.
            if cmds.currentTime( query=True ) != self.currentTime:
                _dbg( 'Restore current time = {}'.format(self.currentTime) )
                cmds.currentTime( self.currentTime )
        except Exception,ex:
            _dbg( '    Oops, error in restoring options ({})'.format(ex) )

        self.needsRestoring = False

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
