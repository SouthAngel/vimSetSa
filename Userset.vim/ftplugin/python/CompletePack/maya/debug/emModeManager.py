"""
Helper class that maintains the EM mode information. Given a string
to specifies an EM mode combination (type +/- evaluators) it will
handle the details regarding translating the mode description into
actions and turning the mode on and off.

String syntax is an abbreviated evaluation mode followed by zero or
more evaluator directives. Regex is [MODE]{[+-]EVALUATOR}*[/NODETYPE

Examples:
    dg            : Turn the EM off and go back to DG mode
    ems           : Turn the EM on and put it into serial mode
    emp           : Turn the EM on and put it into parallel mode
    emp+null      : Turn the EM on and enable the null evaluator
    emp-dynamics  : Turn the EM on and disable the dynamics evaluator
    emp-dynamics+deformer
                  : Turn the EM on, disable the dynamics evaluator, and
                    enable the deformer evaluator
    +cache        : Retain the current EM mode, enable the cache evaluator
    ems+null/transform : Turn the EM on to serial mode and enable the null evaluator
                         for all transform node types.

Calling the setMode() method will put the EM into the named mode.
Calling it again will exit that mode and put it into the new mode,
including unloading any plugins that had to be loaded. Destruction
or reassignment of the manager will restore the EM to the state it
had just before the first time the mode was set.

The node types enabled by any mentioned evaluators is remembered and
restored on exit. Any evaluators not explicitly appearing in the
evaluator directive list will not have its state remembered.

The plugin loading is not magic, it's a hardcoded list in this file.
Update it if you want to handle any new plugins.

The object is set up to use the Python "with" syntax as follows:

    with emModeManager() as mgr:
        mgr.setMode( someMode )

That will ensure the original states are all restored. There's no other
reliable way to do it in Python. If you need different syntax you can
manually call the method to complete the sequence:

    mgr = emModeManager()
    mgr.setMode( someMode )
    mgr.restore()
"""
import re
import maya.cmds as cmds

__all__ = ['emModeManager']

# Set this to true if you wish to see detailed information on exactly what the
# manager is enabling and disabling.
IN_DEBUG_MODE = False

#======================================================================
def _dbg(message):
    '''Print a message only if debugging mode is turned on'''
    if IN_DEBUG_MODE:
        print message

#======================================================================

def _hasEvaluationManager():
    '''Check to see if the evaluation manager is available'''
    return 'evaluationManager' in dir(cmds)

#======================================================================
RE_MODE = re.compile( r'^\s*([^+-]*)(.*)$' )
RE_EVALUATORS = re.compile( r'([+-][^-+/]+)' )
# Some evaluators require plugins, catch the ones we know of
EVALUATOR_PLUGINS = { 'deformer'  : 'deformerEvaluator',
                      'cache'     : 'cacheEvaluator',
                      'null'      : 'nullEvaluator' }

def as_list(thing):
    '''Simple utility to ensure the thing is a list, return None as an empty list'''
    if thing is None:
        return []
    elif isinstance(thing,list):
        return thing
    elif hasattr(thing, '__iter__'):
        return list(thing)
    return list([thing])

class emModeManager(object):
    '''
    Class for managing the EM state in a 'with' format. Remembers and
    restores the EM mode, active evaluators, and the node types enabled on
    those evaluators.
    '''
    #----------------------------------------------------------------------
    def __save_state(self):
        '''
        Remember the current state of all EM related parameters so that they
        can be restored on exit.
        '''
        _dbg( '*** emModeManager::__save_state' )
        self.original_mode = cmds.evaluationManager( mode=True, query=True )[0]
        self.original_evaluators_enabled = as_list(cmds.evaluator( query=True, enable=True))
        self.original_evaluators_disabled = as_list(cmds.evaluator( query=True, enable=False))
        self.original_evaluator_node_types = {}
        for evaluator in self.original_evaluators_enabled + self.original_evaluators_disabled:
            node_types = cmds.evaluator(nodeType=True, query=True, name=evaluator )
            if node_types == None:
                node_types = []
            self.original_evaluator_node_types[evaluator] = node_types
        self.plugins_to_unload = []
        return self

    #----------------------------------------------------------------------
    def __enter__(self):
        _dbg( '*** emModeManager::__enter__' )
        self.__save_state()
        return self

    #----------------------------------------------------------------------
    def __init__(self):
        '''Defining both __enter__ and __init__ so that either one can be used'''
        _dbg( '*** emModeManager::__init__' )
        self.__save_state()

    #----------------------------------------------------------------------
    def __exit__(self,type,value,traceback):
        '''Ensure the state is restored if this object goes out of scope'''
        _dbg( '*** emModeManager::__exit__' )
        _dbg( '    Type = %s' % str(type) )
        _dbg( '    Value = %s' % str(value) )
        _dbg( '    Traceback = %s' % str(traceback) )
        self.restore_state()

    #----------------------------------------------------------------------
    @staticmethod
    def rebuild(include_scheduling=False):
        '''
        Invalidate the EM and rebuild it.
        '''
        cmds.evaluationManager( invalidate=True )
        if include_scheduling:
            # Need to set the time to force the scheduling graph to rebuild too
            cmds.currentTime( cmds.currentTime(query=True) )

    #----------------------------------------------------------------------
    def setMode(self, modeName):
        '''
        Ensure the EM has a named mode set. See class docs for details on mode names.
        The changes are cumulative so long as they don't conflict so this only sets
        the mode to serial:
            self.setMode('emp')
            self.setMode('ems')
        however this will enable both evaluators
            self.setMode('+deformer')
            self.setMode('+cache')

        Changes can also be put into one single string:
            self.setMode( 'ems+deformer+cache' )

        Lastly by using the '/' character as a separator the enabled node types on
        evaluators can also be manipulated:
            self.setMode( 'ems+deformer+cache/+expression-transform' )

        raises SyntaxError if the mode name is not legal
        '''
        _dbg( '*** Setting mode to %s' % modeName )

        # To avoid partial setting the state isn't touched until all mode information
        # has been parsed.
        #
        evaluators_to_enable = []
        evaluators_to_disable = []
        node_types_to_enable = {}
        node_types_to_disable = {}

        match = RE_MODE.match( modeName )
        if match:
            if match.group(1) == 'ems':
                em_mode = 'serial'
            elif match.group(1) == 'emp':
                em_mode = 'parallel'
            elif match.group(1) == 'dg':
                em_mode = 'off'
            elif match.group(1) == '':
                em_mode = cmds.evaluationManager( query=True, mode=True )[0]
            else:
                raise SyntaxError( '%s is not a recognized EM mode' % match.group(1) )

            _dbg( '    +++ Processing evaluator modes {}'.format( match.group(2) ) )

            # Separate the evaluators from the node types
            evaluator_split = match.group(2).split( '/' )
            node_types = evaluator_split[1:]
            node_types_to_add = []
            node_types_to_remove = []

            # Now handle the node type information
            for node_type in node_types:
                _dbg( '       Raw Node type {}'.format( node_type ) )
                action = node_type[0]
                node_type_name = node_type[1:]
                _dbg( '    ... Node type {} {}'.format( action, node_type_name ) )

                # Don't allow both '+' and '-', or even two the same
                if node_type_name in node_types_to_add or node_type_name in node_types_to_remove:
                    raise SyntaxError('Node type {}s was specified twice'.format(node_type_name))

                if action == '+':
                    _dbg( '       Will turn on node type {}'.format( node_type_name ) )
                    node_types_to_add.append( node_type_name )
                elif action == '-':
                    _dbg( '       Will turn off node type {}'.format( node_type_name ) )
                    node_types_to_remove.append( node_type_name )
                else:
                    raise SyntaxError('{} is not a recognized node type mode (+XX or -XX)'.format(node_type))

            # Process the evaluator modes
            eval_matches = RE_EVALUATORS.findall( evaluator_split[0] )
            for eval_match in as_list(eval_matches):
                _dbg( '    ... Processing evaluator mode {}'.format(eval_match) )
                action = eval_match[0]
                evaluator_info = eval_match[1:].split('/')
                evaluator = evaluator_info[0]
                node_types = evaluator_info[1:]

                # Don't allow both '+' and '-', or even two the same
                if evaluator in as_list(evaluators_to_enable) or evaluator in as_list(evaluators_to_disable):
                    raise SyntaxError('Evaluator %s was specified twice' % evaluator)

                if action == '+':
                    _dbg( '       Will turn on %s' % evaluator )
                    evaluators_to_enable.append( evaluator )
                elif action == '-':
                    _dbg( '       Will turn off %s' % evaluator )
                    evaluators_to_disable.append( evaluator )
                else:
                    raise SyntaxError('%s is not a recognized EM evaluator command (+XX or -XX)' % eval_match)

                # Now handle the node type information
                for node_type in as_list(node_types_to_add):
                    node_types_to_enable[ evaluator ] = node_types_to_enable.get(evaluator, []) + [node_type]
                for node_type in as_list(node_types_to_remove):
                    node_types_to_disable[ evaluator ] = node_types_to_disable.get(evaluator, []) + [node_type]
        else:
            raise SyntaxError('%s is not a recognized EM command "{ems|emp|dg}{[+-]XX}*{/[+-]YY}*"' % modeName)

        # Now that the state is prepared switch to the new modes
        cmds.evaluationManager( mode=em_mode )

        # Check to see which evaluators had to be turned on and remember them.
        for turn_on in evaluators_to_enable:
            if turn_on in EVALUATOR_PLUGINS:
                # Check the loaded state first to prevent the warning message if it's already loaded
                if not cmds.pluginInfo( EVALUATOR_PLUGINS[turn_on], query=True, loaded=True ):
                    _dbg( '    Loading plugin %s' % EVALUATOR_PLUGINS[turn_on] )
                    loaded = cmds.loadPlugin( EVALUATOR_PLUGINS[turn_on] )
                else:
                    loaded = None
                # We like to avoid perturbing state so if we loaded the
                # plug-in we'll unload it when done
                if loaded != None:
                    self.plugins_to_unload += loaded
            cmds.evaluator( enable=True, name=turn_on )
            _dbg( '     Enable {}'.format(turn_on) )

        # Check to see which evaluators had to be turned off and remember them.
        for turn_off in evaluators_to_disable:
            cmds.evaluator( enable=False, name=turn_off )
            _dbg( '     Disable {}'.format(turn_off) )

        # If any node type changes were specified do them now
        for (evaluator,node_types) in node_types_to_enable.iteritems():
            for node_type in node_types:
                cmds.evaluator( name=evaluator, enable=True, nodeType=node_type )
                _dbg( '     Enable type {} on {}'.format(node_type,evaluator) )
        for (evaluator,node_types) in node_types_to_disable.iteritems():
            for node_type in node_types:
                cmds.evaluator( name=evaluator, enable=False, nodeType=node_type )
                _dbg( '     Disable type {} on {}'.format(node_type,evaluator) )

    #----------------------------------------------------------------------
    def restore_state(self):
        '''
        Restore the evaluation manager to its original mode prior to creation
        of this object. Using the "with" syntax this will be called automatically.
        You only need to call explicitly when you instantiate the mode manager
        as an object.

        For now the state is brute-force restored to what the original was without
        regards to current settings. The assumptions are that the states are
        independent, and the performance is good enough that it's not necessary to
        remember just the things that were changed.
        '''
        _dbg( '*** emModeManager::restore_state' )

        # Evaluation mode
        _dbg( '     Restore mode to %s' % self.original_mode )
        cmds.evaluationManager( mode=self.original_mode )

        # Evaluators originally on
        for evaluator in self.original_evaluators_enabled:
            _dbg( '     Enabling {}'.format(evaluator) )
            cmds.evaluator( enable=True, name=evaluator )

        # Evaluators originally off
        for evaluator in self.original_evaluators_disabled:
            _dbg( '     Disabling {}'.format(evaluator) )
            cmds.evaluator( enable=False, name=evaluator )

        # Node types for evaluators
        for (evaluator,restored_node_types) in self.original_evaluator_node_types.iteritems():
            # The list of node types is too long to just set/unset everything so instead
            # compare the current list with the original list and toggle on and off as
            # appropriate to restore back to the original.
            current_node_types = cmds.evaluator( name=evaluator, nodeType=True, query=True )
            if current_node_types == None:
                current_node_types = []
            for node_type in current_node_types:
                if node_type not in restored_node_types:
                    _dbg( '     Enabling node type {} on {}'.format(node_type, evaluator) )
                    cmds.evaluator( name=evaluator, nodeType=node_type, enable=False )
            for node_type in restored_node_types:
                if node_type not in current_node_types:
                    _dbg( '     Disabling node type {} on {}'.format(node_type, evaluator) )
                    cmds.evaluator( name=evaluator, nodeType=node_type, enable=True )

        # Plugins we loaded
        for plugin in self.plugins_to_unload:
            try:
                _dbg( '     Unload %s' % plugin )
                cmds.unloadPlugin( plugin )
            except:
                # Just in case someone else already unloaded it
                pass

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
