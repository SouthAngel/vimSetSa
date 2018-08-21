
import maya.app.selectionSet.model.selectionSet as selectionSet

class SelectionSet(object):
    """ This class defines the public 'selection set' concept """

    def __init__(self, name):
        super(SelectionSet, self).__init__()
        self.name = name
        
    def getNodeNames(self):
        """ Get the list of node names defined by the criteria of this Selection Set """
        return []


def create(name):
    """ This method creates a Selection Set with default settings """
    return SelectionSet(name)

def get(name):
    """ This method gets a Selection Set if it exists """
    return SelectionSet(name)

def delete(name):
    """ This method deletes a Selection Set if it exists """
    pass

def getAll():
    """ Get the list of all Selection Sets """
    return []

def deleteAll():
    """ This method deletes all the Selection Sets """
    pass
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
