from PySide2.QtCore import QSize, QEvent
from PySide2.QtGui import QColor, QIcon, QImage, QPainter, QPixmap, qRgba, qAlpha
from PySide2.QtWidgets import QAbstractButton, QStyle, QStyleOptionButton, QToolTip

import maya.app.renderSetup.views.utils as utils


class RenderSetupButton(QAbstractButton):
    """
    This class represents a render setup button which is an icon button that produces a brighter version of the icon when hovered over.
    """

    # Constants
    DEFAULT_BUTTON_SIZE = utils.dpiScale(20)
    HIGH_LIMIT = 205
    LOW_LIMIT = 30
    MAX_VALUE = 255
    ADJUSTMNET = MAX_VALUE - HIGH_LIMIT
    
    def __init__(self, parent, icon, size=DEFAULT_BUTTON_SIZE):
        super(RenderSetupButton, self).__init__(parent)
        self.size = size
        self.setIcon(icon)
        self.enter = False
        self.brighterPixmap = None
       
    def enterEvent(self, event):
        self.enter = True
        self.repaint()

    def leaveEvent(self, event):
        self.enter = False
        self.repaint()
        
    def event(self, event):
        if event.type() == QEvent.ToolTip:
            QToolTip.showText(event.globalPos(), self.toolTip())
            return True

        return super(QAbstractButton, self).event(event)

    def paintEvent(self, e):
        """ Draws the render setup button """
        painter = QPainter(self)
        option = QStyleOptionButton()
        option.initFrom(self)
        if self.isDown():
            option.state = QStyle.State_Sunken
        else:
            option.state = QStyle.State_Raised
         
        if self.enter:
            option.state = option.state | QStyle.State_MouseOver
         
        option.icon = self.icon()
        self.drawControl(QStyle.CE_PushButton, option, painter, self)

    def drawControl(self, element, option, painter, widget = None):
        """ Draws the icon button """
        pixmap = option.icon.pixmap(self.size, self.size)
        if option.state & QStyle.State_MouseOver:
            pixmap = self.generatedIconPixmap(QIcon.Active, pixmap, option)
        painter.drawPixmap(option.rect, pixmap, pixmap.rect())
        
    # Code taken from QadskDarkStyle.cpp - QadskDarkStyle::generatedIconPixmap
    def generatedIconPixmap(self, iconMode, pixmap, option):
        """ Draws the icon button brighter when hovered over. """
        if iconMode == QIcon.Normal:
            return pixmap
        elif iconMode == QIcon.Active:
            if self.brighterPixmap is None:
                img = pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
                imgh = img.height()
                imgw = img.width()
                pixel = None
                for y in range(0, imgh):
                    for x in range(0, imgw):
                        pixel = img.pixel(x, y)
                        color = QColor(pixel)
                        h, s, v, a = color.getHsv()
                        if v > self.LOW_LIMIT: # value below this limit will not be adjusted
                            if  v < self.HIGH_LIMIT: # value above this limit will just max up to 255
                                v = v + self.ADJUSTMNET
                            else:
                                v = self.MAX_VALUE
                        color.setHsv(h,s,v)
                        img.setPixel(x, y, qRgba(color.red(), color.green(), color.blue(), qAlpha(pixel)))
                self.brighterPixmap = QPixmap.fromImage(img)
            return self.brighterPixmap

    def sizeHint(self):
        return QSize(self.size, self.size)# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
