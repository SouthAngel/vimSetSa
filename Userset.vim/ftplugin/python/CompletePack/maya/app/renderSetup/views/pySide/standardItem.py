from PySide2.QtGui import QStandardItem

class StandardItem(QStandardItem):

    def depth(self):
        return 0 if self.parent() is None else 1 + self.parent().depth()

    def __eq__(self, o):
        # The default QStandardItem:__eq__() method is not implemented
        # https://bugreports.qt.io/browse/PYSIDE-74
        return id(self)==id(o)
    
    def __ne__(self, o):
        # The default QStandardItem:__ne__() method is not implemented
        # https://bugreports.qt.io/browse/PYSIDE-74
        return not self.__eq__(o)

# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
