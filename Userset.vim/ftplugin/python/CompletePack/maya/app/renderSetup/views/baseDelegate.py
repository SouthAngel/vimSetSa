from PySide2.QtCore import QPointF, Qt, QRect
from PySide2.QtGui import QColor, QPalette, QPen, QCursor
from PySide2.QtWidgets import QStyle, QStyledItemDelegate

from copy import deepcopy
import weakref
import maya.app.renderSetup.views.utils as utils

""" Create a pixmap scales to the size we expect icons to be for render setup.
    Helps unify things when using icons of different sizes """
def createPixmap(fileName):    
    return utils.createPixmap(fileName, utils.dpiScale(20), utils.dpiScale(20))
    
class BaseDelegate(QStyledItemDelegate):
    """
    This class provides customization of the appearance of items in a Model.
    """

    # Constants
    ARROW_COLOR = QColor(189, 189, 189)
    DISABLED_BACKGROUND_IMAGE = utils.createPixmap(":/RS_disabled_tile.png")
    DISABLED_HIGHLIGHT_IMAGE = utils.createPixmap(":/RS_disabled_tile_highlight.png")
    COLOR_BAR_WIDTH = utils.dpiScale(6)
    TEXT_LEFT_OFFSET = utils.dpiScale(22)
    TEXT_RIGHT_OFFSET = utils.dpiScale(36)
    LAYER_TEXT_RIGHT_OFFSET = utils.dpiScale(70)
    COLLECTION_TEXT_RIGHT_OFFSET = utils.dpiScale(90)

    BOTTOM_GAP_OFFSET = utils.dpiScale(2)
    EXPANDED_ARROW_OFFSET = utils.dpiScale(3.0)
    COLLAPSED_ARROW_OFFSET = utils.dpiScale(6.0)
    EXPANDED_ARROW = (utils.dpiScale(QPointF(0.0, 11.0)), utils.dpiScale(QPointF(10.0, 11.0)), utils.dpiScale(QPointF(5.0, 16.0)))
    COLLAPSED_ARROW = (utils.dpiScale(QPointF(0.0, 8.0)), utils.dpiScale(QPointF(5.0, 13.0)), utils.dpiScale(QPointF(0.0, 18.0)))

    LAST_ICON_RIGHT_OFFSET = utils.dpiScale(24)
    ICON_WIDTH = utils.dpiScale(20)
    WARNING_ICON_WIDTH = utils.dpiScale(11)
    ICON_TOP_OFFSET = utils.dpiScale(4)

    ACTION_BORDER = utils.dpiScale(2)
    ACTION_WIDTH = utils.dpiScale(24) # ICON_WIDTH + (2*ACTION_BORDER)

    VISIBILITY_IMAGE = utils.createPixmap(":/RS_visible.png")
    RENDERABLE_IMAGE = utils.createPixmap(":/RS_render.png")
    WARNING_IMAGE    = utils.createPixmap(":/RS_warning.png")

    def __init__(self, treeView):
        super(BaseDelegate, self).__init__()
        self.treeView = weakref.ref(treeView)
        self.lastHitAction = None

    def _getItem(self, index):
        """ Override this function to return the item associated with the provided index. NOTE: Do not implement this function directly! """
        pass

    def _drawColorBar(self, painter, rect, item):
        """ Override this function to draw a color bar in front of the filled portion of the row. NOTE: Do not implement this function directly! """
        pass

    def _drawFill(self, painter, rect, item, isHighlighted, highlightColor):
        """ Override this function to draw the fill. NOTE: Do not implement this function directly! """
        pass

    def _drawArrow(self, painter, rect, item):
        painter.save()
        if item.rowCount() != 0:
            arrow = None
            if self.treeView().isExpanded(item.index()):
                painter.translate(rect.left() + self.EXPANDED_ARROW_OFFSET, rect.top())
                arrow = self.EXPANDED_ARROW
            else:
                painter.translate(rect.left() + self.COLLAPSED_ARROW_OFFSET, rect.top())
                arrow = self.COLLAPSED_ARROW
            oldBrush = painter.brush()
            painter.setBrush(self.ARROW_COLOR)
            painter.setPen(Qt.NoPen)
            painter.drawPolygon(arrow)
            painter.setBrush(oldBrush)
        painter.restore()

    def _drawText(self, painter, rect, item):
        oldPen = painter.pen()
        painter.setPen(QPen(item.data(Qt.TextColorRole), 1))
        painter.setFont(item.data(Qt.FontRole))
        textRect = self.getTextRect(rect, item)
        painter.drawText(textRect, item.data(Qt.TextAlignmentRole), item.data(Qt.DisplayRole))
        painter.setPen(oldPen)

    def _drawWarning(self, painter, rect, item):
        pass

    def getTextRect(self, rect, item):
        textRect = deepcopy(rect)
        textRect.setLeft(textRect.left() + self.TEXT_LEFT_OFFSET)
        textRect.setRight(textRect.right() - self.TEXT_RIGHT_OFFSET)
        return textRect

    def _addActionIcons(self, painter, rect, item, highlightedColor):
        """ Override this function to draw the action icons (visibility, renderability, etc). NOTE: Do not implement this function directly! """
        pass

    def drawToolbarFrame(self, painter, rect, toolbarCount):
        # draw the darkened toolbar background
        if toolbarCount > 0:
            top = rect.top() + self.ICON_TOP_OFFSET
            backGroundColor = QColor(55, 55, 55)
            toolbarLength = toolbarCount*self.ACTION_WIDTH + (2*self.ACTION_BORDER)
            left = rect.right() - (toolbarLength + self.ACTION_BORDER)
            left = left if left > 0 else 0
            painter.setOpacity(0.8)
            painter.fillRect(left, top-self.ACTION_BORDER, toolbarLength, self.ACTION_WIDTH, backGroundColor)
            painter.setOpacity(1.0)

    def drawPixmap(self, painter, pixmap, left, top):
        painter.drawPixmap(QRect(left, top, self.ICON_WIDTH, self.ICON_WIDTH), pixmap)

    def drawAction(self, painter, actionName, pixmap, left, top, highlightedColor, drawDisclosure, borderColor):
        if (pixmap != None):
            iconRect = QRect(left, top, self.ICON_WIDTH, self.ICON_WIDTH)
            if highlightedColor is not None:
                painter.fillRect(iconRect, highlightedColor)

            # draw the icon.  Its opacity depends on mouse over.
            p = self.treeView().mapFromGlobal(QCursor.pos())
            if not iconRect.contains(p):
                painter.setOpacity(0.7)
            else:
                painter.setOpacity(1.0)
                self.lastHitAction = actionName
            self.drawPixmap(painter, pixmap, left, top)
            painter.setOpacity(1.0)

            if drawDisclosure:
                painter.drawPixmap(iconRect, self.DISCLOSURE_IMAGE)

            if borderColor:
                oldPen = painter.pen()
                painter.setPen(QPen(borderColor, 1))
                painter.drawRect(iconRect)
                painter.setPen(oldPen)

    def paint(self, painter, option, index):
        """ Renders the delegate using the given painter and style option for the item specified by index. """

        # If the index is invalid we have nothing to draw
        if not index.isValid():
            return
        
        item = self._getItem(index)
        indent = item.depth() * self.treeView().indentation()
        rect = deepcopy(option.rect)
        rect.setLeft(indent)
        rect.setBottom(rect.bottom() - self.BOTTOM_GAP_OFFSET)
        isHighlighted = option.showDecorationSelected and option.state & QStyle.State_Selected
        highlightedColor = option.palette.color(QPalette.Highlight)

        self._drawColorBar(painter, rect, item)
        self._drawFill(painter, rect, item, isHighlighted, highlightedColor)
        self._drawArrow(painter, rect, item)
        self._drawText(painter, rect, item)
        self._addActionIcons(painter, rect, item, highlightedColor)
        self._drawWarning(painter, rect, item)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
