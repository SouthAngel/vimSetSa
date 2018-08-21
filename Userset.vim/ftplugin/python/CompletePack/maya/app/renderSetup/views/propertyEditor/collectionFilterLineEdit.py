import maya
maya.utils.loadStringResourcesForModule(__name__)

from PySide2.QtWidgets import QLineEdit

import maya.cmds as cmds

class CollectionFilterLineEdit(QLineEdit):
    def __init__(self, text=None, parent=None):
        super(CollectionFilterLineEdit, self).__init__(text=text, parent=parent)
        self.setAcceptDrops(True)
        tip = maya.stringTable['y_collectionFilterLineEdit.kCustomFilterTooltipStr' ]
        tip += maya.stringTable['y_collectionFilterLineEdit.kCustomFilterTooltipStr1' ]
        tip += maya.stringTable['y_collectionFilterLineEdit.kCustomFilterTooltipStr2' ]
        tip += maya.stringTable['y_collectionFilterLineEdit.kCustomFilterTooltipStr3' ]
        tip += '\tshader/surface -blinn'

        self.setToolTip(tip)
        
    def _textContainsCommands(self, text):
        """ Determines whether all objects separated by a newline character exist or not """
        objs = text.rstrip().split('\n')
        for i in range(0, len(objs)):
            if not cmds.objExists(objs[0]):
                return False
        return True

    def dragEnterEvent(self, event):
        """ Accepts drag events if the dragged event text contains only commands """
        if event.mimeData().hasText() and self._textContainsCommands(event.mimeData().text()):
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """ Accepts drag move events. Validation is already done in the enter event"""
        event.accept()


    def dropEvent(self, event):
        """ Adds the dropped object types to the list """
        text = self.text()
        names = event.mimeData().text().rstrip().split('\n')
        for i in range(0, len(names)):
            typeStr = cmds.objectType(names[i])
            if (len(text) > 0):
                text += " "
            if typeStr not in text:
                text += typeStr

        self.setText(text)
        self.editingFinished.emit()# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
