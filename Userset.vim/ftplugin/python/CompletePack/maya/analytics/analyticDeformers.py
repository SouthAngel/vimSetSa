"""
Analytic class for examining deformer usage
"""
import re
import maya.cmds as cmds
from .BaseAnalytic import BaseAnalytic, OPTION_DETAILS
from .decorators import addMethodDocs,addHelp,makeAnalytic

RE_VERTEX = re.compile( r'vtx\[([0-9]+)\]' )
RE_VERTEX_PAIR = re.compile( r'vtx\[([0-9]+):([0-9]+)\]' )
RE_VERTEX_ALL = re.compile( r'vtx\[\*\]' )

@addMethodDocs
@addHelp
@makeAnalytic
class analyticDeformers(BaseAnalytic):
    """
    Analyze type and usage of single deformers and deformer chains.
    """
    def run(self):
        """
        Examine the meshes in the scene for deformation. There will be two
        types of data in the output file under the column headings
        'Deformer','Member','Value':
            - Deformer Name, Member Object, Membership Information, Member Count
                One line per object being affected by the deformer
            - Deformer Name, '', Name of next deformer in the chain, Deformer Chain length
                Only if more than one deformer is being applied to the same object

        If the 'details' option is not set then the Member Information is omitted,
        otherwise it will be a selection-list format of all members on that
        object subject to deformation by the given deformer.
        """
        self._output_csv( [ 'Deformer'
                          , 'Member'
                          , 'Value'
                          , 'Count'
                          ] )

        meshList = cmds.ls( type='mesh' )
        try:
            if len(meshList) == 0:
                self.warning( 'No meshes to check' )
                return
        except Exception, ex:
            # If the 'ls' command returns None this is the easiest
            # way to trap that case.
            self.warning( 'Mesh check failed ({0:s})'.format(str(ex)) )
            return

        # Tweak nodes are not considered deformations by themselves,
        # though in the node type hierarchy they are siblings to all other
        # deformers. This filters them out while collecting all deformers.
        try:
            deformers = [n for n in cmds.ls( type='geometryFilter' ) if cmds.nodeType(n) != 'tweak']
        except Exception, ex:
            self.warning( 'Deformer check failed ({0:s})'.format(str(ex)) )
            return

        self._set_node_name_count( len(meshList) )
        for mesh in meshList:
            history = cmds.listHistory( mesh )
            deformerChain = []
            for historyNode in history:
                if historyNode in deformers:
                    deformerChain.append( historyNode )

            if len(deformerChain) == 0:
                continue

            for deformer in deformerChain:

                # Default to the entire mesh being deformed
                componentCount = cmds.polyEvaluate( mesh, vertex=True )
                componentList = ['vtx[*]']

                # Check for group parts selecting a portion of the surface
                groupPartList = []
                gpConnections = cmds.listConnections( '%s.input' % deformer )
                if gpConnections != None:
                    groupPartList = [gp for gp in gpConnections if cmds.nodeType(gp) == 'groupParts']

                for groupParts in groupPartList:
                    # Match up the group parts found with the mesh being checked.
                    groupId = [gi for gi in cmds.listConnections( '%s.groupId' % groupParts ) if cmds.nodeType(gi) == 'groupId']
                    if groupId != None:
                        grouping = cmds.listConnections( '%s.groupId' % groupId[0] )
                        if mesh not in grouping:
                            continue

                    componentCount = 0
                    componentList = cmds.getAttr('%s.inputComponents' % groupParts)
                    for component in componentList:
                        # vtx[N]  single vertex N
                        vtxMatch = RE_VERTEX.match( component )
                        if vtxMatch:
                            componentCount += 1
                            continue
                        # vtx[N:M]  range of vertices from N to M
                        vtxPairMatch = RE_VERTEX_PAIR.match( component )
                        if vtxPairMatch:
                            componentCount += (int(vtxPairMatch.group(2)) - int(vtxPairMatch.group(1)) + 1)
                            continue
                        # vtx[*]  all vertices in the object
                        if RE_VERTEX_ALL.match( component ):
                            componentCount = cmds.polyEvaluate( mesh, vertex=True )
                            continue
                        self.warning( 'Unrecognized group parts component pattern {0:s}'.format( str(component) ) )

                if self.option(OPTION_DETAILS):
                    components = ' '.join( componentList )
                else:
                    components = ''

                self._output_csv( [ self._node_name(deformer), self._node_name(mesh), components, componentCount ] )

            for i in range(0, len(deformerChain)-1):
                self._output_csv( [ self._node_name(deformerChain[i])
                                  , ''
                                  , self._node_name(deformerChain[i+1])
                                 , str(len(deformerChain))
                                 ] )

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
