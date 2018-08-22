from PySide2.QtGui import QCursor
from PySide2.QtWidgets import QMenu, QToolTip

"""
    Unfortunately, the tooltip of an action does not appear by default when the action is not in a toolbar.
    
    Implemented the solution found here
    http://stackoverflow.com/questions/21725119/why-wont-qtooltips-appear-on-qactions-within-a-qmenu

    Note: Another workaround would have been to use the status tip so that the 'hack' below 
    would not have been needed; however, the status bar is quite far from the template menu 
    (bottom of Maya window) so it becomes less usefull.
    
"""

class Menu(QMenu):

    def __init__(self, parent=None):
        super(Menu, self).__init__(parent)
        self.hovered.connect(self.handleMenuHovered)

    def __init__(self, title, parent=None):
        super(Menu, self).__init__(title, parent)
        self.hovered.connect(self.handleMenuHovered)
        
    def handleMenuHovered(self, action):
        if action.toolTip() != action.iconText():
            # Bypass the default mechanism which displays the action name when
            # the tooltip is not present because it does not add any pertinent information to the user,
            # does not offer the multi-line.
            QToolTip.showText(QCursor.pos(), action.toolTip(), self, self.actionGeometry(action))
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
