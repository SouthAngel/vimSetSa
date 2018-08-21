from PySide2.QtCore import QRect, Qt, Signal
from PySide2.QtGui import QBrush, QColor, QFontMetrics, QPainter, QPen, QTextOption
from PySide2.QtWidgets import QFrame, QLineEdit, QHBoxLayout, QVBoxLayout

import maya.app.renderSetup.views.utils as utils

from maya.app.renderSetup.views.baseDelegate import BaseDelegate
import maya.app.renderSetup.views.proxy.renderSetup as renderSetup
import maya.app.renderSetup.views.proxy.renderSetupRoles as renderSetupRoles

import weakref


"""
The code in this file is used to specify a frame layout in PySide and is a modified version of the public domain code taken from: http://pastebin.com/qYgDDYsB
The code is discussed in this forum post: https://groups.google.com/forum/#!topic/python_inside_maya/vO1pvA4YhF0
"""

class Frame(QFrame):
    def __init__(self, item, parent):
        super(Frame, self).__init__(parent=parent)
        self.item = weakref.ref(item)

    def _drawBackground(self, painter, e):
        if self.item():
            painter.fillRect(e.rect(), self.item().data(Qt.BackgroundRole))
            if not self.item().data(renderSetupRoles.NODE_ENABLED):
                painter.drawTiledPixmap(e.rect(), BaseDelegate.DISABLED_BACKGROUND_IMAGE)

class CollapsibleArrowAndTitle(Frame):
    """
    This class defines the arrow used for a FrameLayout
    """

    # Constants
    WIDTH = utils.dpiScale(33)
    HEIGHT = utils.dpiScale(28)
    ARROW_COLOR = QColor(192, 192, 192)
    COLOR_BAR_WIDTH = utils.dpiScale(7)
    COLOR_BAR_HEIGHT = utils.dpiScale(28)
    EXPANDED_ARROW_OFFSET = utils.dpiScale(10.0)
    COLLAPSED_ARROW_OFFSET = utils.dpiScale(13.0)
    NODE_TYPE_TEXT_RECT = QRect(utils.dpiScale(20), 0, utils.dpiScale(1000), HEIGHT)

    def __init__(self, item, parent):
        super(CollapsibleArrowAndTitle, self).__init__(item, parent=parent) 
        self.isCollapsed = False
        fontMetric = QFontMetrics(self.item().data(Qt.FontRole))
        text = self.item().data(renderSetupRoles.NODE_TYPE_STR)
        self.setMinimumSize(self.WIDTH + fontMetric.width(text), self.HEIGHT)
        self.arrowPoints = BaseDelegate.EXPANDED_ARROW

    def setArrow(self, isCollapsed):
        """ Sets the arrow direction """
        self.arrowPoints = BaseDelegate.EXPANDED_ARROW if isCollapsed else BaseDelegate.COLLAPSED_ARROW

    def paintEvent(self, e):
        """ Draws the color bar and arrow """
        if self.item():
            painter = QPainter(self)
            
            # Draws the color bar
            painter.setPen(Qt.NoPen)
            rect = QRect(0, 0, self.COLOR_BAR_WIDTH, self.COLOR_BAR_HEIGHT)
            painter.fillRect(rect, self.item().data(renderSetupRoles.NODE_COLOR_BAR))
            oldBrush = painter.brush()
            
            if self.item().type()==renderSetup.RENDER_OVERRIDE_TYPE and self.item().isLocalRender():
                diameter = rect.width()-2
                rect2 = QRect(rect.x()+1, rect.y() + (rect.height()-diameter)/2, diameter, diameter)
                brush = painter.brush()
                pen = painter.pen()
                hints = painter.renderHints()
            
                painter.setRenderHint(QPainter.Antialiasing, on=True)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor(67,79,70), style=Qt.SolidPattern))
                painter.drawEllipse(rect2)
            
                painter.setRenderHints(hints)
                painter.setPen(pen)
                painter.setBrush(brush)

            # Draws the arrow
            painter.setBrush(self.ARROW_COLOR)
            if self.arrowPoints == BaseDelegate.EXPANDED_ARROW:
                painter.translate(self.EXPANDED_ARROW_OFFSET, 0.0)  
            else:
                painter.translate(self.COLLAPSED_ARROW_OFFSET, 0.0)
            painter.drawPolygon(self.arrowPoints)
            painter.setBrush(oldBrush)

            # Draws the node type text
            painter.setPen(QPen(self.item().data(Qt.TextColorRole)))
            text = self.item().data(renderSetupRoles.NODE_TYPE_STR)
            painter.setFont(self.item().data(Qt.FontRole))
            painter.drawText(self.NODE_TYPE_TEXT_RECT, text, QTextOption(Qt.AlignLeft | Qt.AlignVCenter))


class NameLineEdit(QLineEdit):
    """
    This class is used to display the editable name associated with a 
    collection, layer, or override.
    """
    def __init__(self, item, parent):
        super(NameLineEdit, self).__init__(parent)
        self.item = weakref.ref(item)
        self.setText(self.item().data(Qt.EditRole))
        self.editingFinished.connect(self.nameChanged)
        self.hasFocus = False

    def nameChanged(self):
        self.item().setData(self.text(), Qt.EditRole)
        
        # If the name is already in use we'll assign a different name and need
        # to update the UI.
        name = self.item().data(Qt.EditRole)
        if self.text() != name:
            self.setText(name)
        self.clearFocus()
    
    def focusInEvent(self, event):
        self.hasFocus = True
        super(NameLineEdit, self).focusInEvent(event)

    def focusOutEvent(self, event):
        self.hasFocus = False
        super(NameLineEdit, self).focusOutEvent(event)

    def keyPressEvent(self, event):
        # When the escape key is pressed we want to revert back to the previous
        # result
        if event.key() == Qt.Key_Escape:
            self.setText(self.item().data(Qt.EditRole))
            self.clearFocus()
        super(NameLineEdit, self).keyPressEvent(event)

    def paintEvent(self, event):
        # If we don't have focus, then update the name to match the edit role
        # on updates.
        if self.item() and not self.hasFocus:
            name = self.item().data(Qt.EditRole)
            if self.text() != name:
                self.setText(name)

        super(NameLineEdit, self).paintEvent(event)


class TitleFrame(Frame):
    """
    This class defines the frame for the FrameLayout
    """

    # Constants
    FRAME_HEIGHT = utils.dpiScale(28)
    
    # Signals
    clicked = Signal()
    
    def __init__(self, item, parent):
        super(TitleFrame, self).__init__(item, parent=parent)

        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0,0,0,0)
        self.arrowAndTitle = CollapsibleArrowAndTitle(self.item(), self)
        self.layout.addWidget(self.arrowAndTitle)
        if self.item().data(renderSetupRoles.NODE_SHOULD_DISPLAY_NAME):
            self.name = NameLineEdit(self.item(), self)
            self.layout.addWidget(self.name)
            self.layout.addSpacing(utils.dpiScale(16))
        self.setLayout(self.layout)

    def paintEvent(self, e):
        """ Draws the disabled or enabled title frame background. """
        painter = QPainter(self)
        self._drawBackground(painter, e)
        
    def mousePressEvent(self, event):
        self.clicked.emit()
        return super(TitleFrame, self).mousePressEvent(event)
        
class FrameLayout(QFrame):
    """
    This class defines the FrameLayout which emulates the behaviour of the Maya Python API's maya.cmds.frameLayout function. 
     The only difference is that the render setup version also provides a color bar and background color to differentiate layers, 
     collections, and overrides.
    """

    def __init__(self, item, parent):
        super(FrameLayout, self).__init__(parent)
        self.item = weakref.ref(item)
        self.isCollapsed = False
        self.mainLayout = None
        self.titleFrame = None
        self.contentFrame = None
        self.contentLayout = None

        self.initFrameLayout()

    def addWidget(self, widget):
        self.contentLayout.addWidget(widget)

    def getWidget(self, index):
        return self.contentLayout.itemAt(index).widget() if self.contentLayout.count() > index else None

    def initMainLayout(self):
        self.mainLayout = QVBoxLayout()
        self.mainLayout.setContentsMargins(0, 0, 0, 0)
        self.mainLayout.setSpacing(0)
        self.setLayout(self.mainLayout)
        
    def initTitleFrame(self):
        self.titleFrame = TitleFrame(self.item(), self)
        self.mainLayout.addWidget(self.titleFrame)
        
    def initContentFrame(self):
        self.contentFrame = QFrame()
        self.contentFrame.setContentsMargins(0, 0, 0, 0)
        
        self.contentLayout = QVBoxLayout()
        self.contentLayout.setContentsMargins(0, 0, 0, 0)
        self.contentLayout.setSpacing(0)
        self.contentFrame.setLayout(self.contentLayout)
        self.mainLayout.addWidget(self.contentFrame)
 
    def toggleCollapsed(self):
        """ When the title frame is clicked, this function is called to toggle the collapsed state """
        self.isCollapsed = not self.isCollapsed
        self.contentFrame.setVisible(self.isCollapsed)
        self.titleFrame.arrowAndTitle.setArrow(self.isCollapsed)
        self.update()
        
    def initFrameLayout(self):
        self.setContentsMargins(0, 0, 0, 0)
        
        self.initMainLayout()
        self.initTitleFrame()
        self.initContentFrame()

        self.titleFrame.clicked.connect(self.toggleCollapsed)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
