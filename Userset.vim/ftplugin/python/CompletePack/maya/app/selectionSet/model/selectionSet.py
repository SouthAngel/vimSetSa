class SelectionSet( object ):
    """
    This class defines DG behavior related to the 'selection set'.
    
    Note: This class keeps nothing in memory. The way to retrieve the information 
          is to query the DG using the name to build the DG path
    """

    def __init__(self, name, tobeCreated):
        super(SelectionSet, self).__init__()
        self.name = name

        if toBeCreated:
            # Create the corresponding DG node(s)
            pass

    def _getDGPath(self):
        """ Convert the name to a DG path """
        return ""


def get(name):
    """ Get a specific Selection Set """
    return SelectionSet(name, False)

def create(name):
    """ Create a specific Selection Set """
    return SelectionSet(name, True)

def getAll(selectedNodesOnly, parentNameFiler):
    """ Get the list of all Selection Sets """
    return []
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
