"""
Analytic class for examining character data
"""
import maya.cmds as cmds
from .BaseAnalytic import BaseAnalytic, OPTION_DETAILS
from .decorators import addMethodDocs,addHelp,makeAnalytic

@addMethodDocs
@addHelp
@makeAnalytic
class analyticCharacter(BaseAnalytic):
    """
    Analyze the DG connectivity.
    """
    def run(self):
        """
        Examine the characters in the scene for a few basic structure
        elements. The CSV file headings are generic so as to maximize the
        ability to process the data - 'Character','Type','Value'.

        When the 'details' option is set then the data looks like this:
            - Character Name, 'Member', Character Member Plug name
            - Character Name, 'Map', Character to which it is mapped

        otherwise it looks like this
            - Character Name, 'Member', Number of members in the character
            - Character Name, 'Map', Character to which it is mapped
        """
        self._output_csv( [ 'Character'
                         , 'Type'
                         , 'Value'
                         ] )

        characterList = cmds.ls( type='character' )
        try:
            if len(characterList) == 0:
                self.warning( 'No characters to report' )
                return
        except Exception, ex:
            # If the 'character' command returns None this is the easiest
            # way to trap that case.
            self.warning( 'Character report failed ({0:s}'.format(str(ex)) )
            return

        for character in characterList:
            characterName = self._node_name(character)
            memberList = cmds.character( character, query=True )
            if memberList == None:
                memberList = []
            if self.option(OPTION_DETAILS):
                for member in memberList:
                    self._output_csv( [ character, 'Member', member ] )
            else:
                self._output_csv( [ characterName, 'Member', str(len(memberList)) ] )

            # This O(N^2) check for character maps is easier than looking
            # through connections. It's only necessary because the
            # 'characterMap' command can only be queried with both
            # characters as arguments.
            for character2 in characterList:
                # Not sure why Maya thinks a character maps onto itself.
                if character2 == character:
                    continue
                if cmds.characterMap( [character, character2], query=True ) != None:
                    character2Name = self._node_name(character2)
                    self._output_csv( [ characterName, 'Map', character2Name ] )

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
