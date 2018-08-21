'''
A collection of utilities to help manage and inspect the frozen states.
Import all of the utilities to be able to use them.

from maya.debug.frozenUtilities import *
'''
import re
import json
import maya.cmds as cmds

# For convenience this list is in the order they appear in this file
__all__ = [ 'freeze_nodes'
          , 'unfreeze_nodes'
          , 'list_frozen'
          , 'list_frozen_in_scheduling'
          , 'FrozenOptionsManager']

RE_FROZEN_CLUSTER = re.compile( r'frozen\|.*' )

#======================================================================
def freeze_nodes(nodes):
    '''
    Sets the frozen attribute on the list of nodes passed in to True.
    Returns the list of nodes whose value was set. Usually it will be
    all nodes but some locked nodes may not have been set.
    '''
    nodes_set = []
    for node in nodes:
        try:
            cmds.setAttr( '{}.fzn'.format(node), True )
            nodes_set.append( node )
        except:
            pass
    return nodes_set

#======================================================================
def unfreeze_nodes(nodes=None):
    '''
    Sets the frozen attribute on the list of nodes passed in to False.
    If None is passed in then all nodes with the frozen attribute set
    have it cleared.

    Returns the list of nodes whose value was set. Usually it will be
    all nodes but some locked nodes may not have been set.
    '''
    if nodes is None:
        nodes = list_frozen()
    nodes_set = []
    for node in nodes:
        try:
            cmds.setAttr( '{}.fzn'.format(node), False )
            nodes_set.append( node )
        except:
            pass
    return nodes_set

#======================================================================
def list_frozen():
    '''Returns a list of all nodes with the frozen attribute set'''
    return [node for node in cmds.ls() if cmds.getAttr('%s.frozen' % node)]

#======================================================================
def list_frozen_in_scheduling():
    '''
    Returns a list of all nodes that were frozen either directly or
    indirectly as a result of the frozen evaluator settings.

    If no cluster information is available a TypeError is raised.
    If the frozen evaluator is not enabled an AttributeError is raised.
    '''
    if 'frozen' not in cmds.evaluator( enable=True, query=True ):
        raise AttributeError( 'Frozen evaluator is not active' )

    frozen_nodes = []
    try:
        clusters = json.loads( cmds.dbpeek( op='graph', evaluationGraph=True, all=True, a='scheduling') )['scheduling']['Clusters']
        for cluster_name, cluster_members in clusters.iteritems():
                if RE_FROZEN_CLUSTER.match( cluster_name ):
                    frozen_nodes += cluster_members
    except:
        # If an exception was raised it was probably due to the dbpeek command not
        # returning scheduling information, which only happens when the graph is
        # not available
        raise TypeError( 'Cluster information is not available, evaluation graph needs rebuilding' )

    return frozen_nodes

#======================================================================
class FrozenOptionsManager(object):
    '''
    Helper class to manage scoping of a set of frozen options.

        with FrozenOptionsManager() as mgr:
            mgr.setOptions(...)
    '''
    #----------------------------------------------------------------------
    def __init__(self):
        '''This is defined in parallel with __enter__ so that either can be used'''
        self.__save_state()

    #----------------------------------------------------------------------
    def __enter__(self):
        '''Enter the scope of the manager, remembering current values'''
        self.__save_state()
        return self

    #----------------------------------------------------------------------
    def __exit__(self,type,value,traceback):
        '''Exit the scope of the manager, restoring remembered values'''
        self.__restore_state()

    #----------------------------------------------------------------------
    def __save_state( self ):
        '''Remember all of the current values of the freeze options.'''
        self.displayLayers       = cmds.freezeOptions( query=True, displayLayers=True )
        self.downstream          = cmds.freezeOptions( query=True, downstream=True )
        self.explicitPropagation = cmds.freezeOptions( query=True, explicitPropagation=True )
        self.invisible           = cmds.freezeOptions( query=True, invisible=True )
        self.referencedNodes     = cmds.freezeOptions( query=True, referencedNodes=True )
        self.runtimePropagation  = cmds.freezeOptions( query=True, runtimePropagation=True )
        self.upstream            = cmds.freezeOptions( query=True, upstream=True )

    #----------------------------------------------------------------------
    def __restore_state( self ):
        '''Restore all of the remembered values to the freeze options.'''
        cmds.freezeOptions( displayLayers=self.displayLayers )
        cmds.freezeOptions( downstream=self.downstream )
        cmds.freezeOptions( explicitPropagation=self.explicitPropagation )
        cmds.freezeOptions( invisible=self.invisible )
        cmds.freezeOptions( referencedNodes=self.referencedNodes )
        cmds.freezeOptions( runtimePropagation=self.runtimePropagation )
        cmds.freezeOptions( upstream=self.upstream )

    #----------------------------------------------------------------------
    def set_options( self,
                     displayLayers=None,
                     downstream=None,
                     explicitPropagation=None,
                     invisible=None,
                     referencedNodes=None,
                     runtimePropagation=None,
                     upstream=None ):
        '''
        Initialize the options. Everything that is not explicitly set
        is turned off.
        '''
        try:
            cmds.freezeOptions( displayLayers=displayLayers or False )
            cmds.freezeOptions( downstream=downstream or 'none' )
            cmds.freezeOptions( explicitPropagation=explicitPropagation or False )
            cmds.freezeOptions( invisible=invisible or False )
            cmds.freezeOptions( referencedNodes=referencedNodes or False )
            cmds.freezeOptions( runtimePropagation=runtimePropagation or False )
            cmds.freezeOptions( upstream=upstream or 'none' )
        except Exception,ex:
            print 'ERR: Could not set options - {}'.format(ex)

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
