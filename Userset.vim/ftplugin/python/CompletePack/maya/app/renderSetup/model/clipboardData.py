class ClipboardData(object):
    def __init__(self, typeName, parentTypeName):
        self._typeName = typeName
        self._parentTypeName = parentTypeName
    
    def typeName(self):
        # typeName was not made a property for interface compatibility with render setup node classes.
        return self._typeName

    @property
    def parentTypeName(self):
        return self._parentTypeName
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
