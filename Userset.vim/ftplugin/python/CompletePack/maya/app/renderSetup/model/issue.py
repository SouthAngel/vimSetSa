
class Issue(object):
    '''Class representing an issue that contains 
    - a description (a short string explaining what's the issue)
    - a type, mostly used for UI purpose (icon for the issue will be RS_<type>.png)
    - a callback to resolve the issue (assisted resolve).'''
    
    def __init__(self, description, type="warning", resolveCallback=None):
        super(Issue, self).__init__()
        self._description = description
        self._type = type
        self._resolveCallback = resolveCallback
    
    @property
    def description(self):
        return self._description
    
    @property
    def type(self):
        return self._type
    
    def __hash__(self):
        return hash(self._description)
    
    def __eq__(self, o):
        return self._description == o._description

    def __str__(self):
        return self._description
    
    def resolve(self):
        self._resolveCallback()
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
