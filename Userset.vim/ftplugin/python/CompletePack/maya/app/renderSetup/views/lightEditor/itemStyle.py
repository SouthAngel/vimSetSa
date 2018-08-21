from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *

import maya.app.renderSetup.views.utils as utils

class ItemStyle(QCommonStyle):
	""" This class defines the view item style and is only used when style sheets and the delegate are not sufficient. """

	# Constants
	DROP_INDICATOR_COLOR = QColor(255, 255, 255)
	DROP_INDICATOR_WIDTH = utils.dpiScale(3)
	DROP_INDICATOR_LEFT_OFFSET = utils.dpiScale(-25)

	def __init__(self, parent):
		self.__parent = parent
		super(ItemStyle, self).__init__()

	def drawComplexControl(self, control, option, painter, widget = None):
		return self.__parent.drawComplexControl(control, option, painter, widget)

	def drawControl(self, element, option, painter, widget = None):
		return self.__parent.drawControl(element, option, painter, widget)

	def drawItemPixmap(self, painter, rectangle, alignment, pixmap):
		return self.__parent.drawItemPixmap(painter, rectangle, alignment, pixmap)

	def drawItemText(self, painter, rectangle, alignment, palette, enabled, text, textRole = QPalette.NoRole):
		return self.__parent.drawItemText(painter, rectangle, alignment, palette, enabled, text, textRole)

	def drawPrimitive(self, element, option, painter, widget = None):
		""" Draws the given primitive element with the provided painter using the style options specified by option. """
		# Changes the way the drop indicator is drawn
		if element == QStyle.PE_IndicatorItemViewItemDrop and not option.rect.isNull():
			painter.save()
			painter.setRenderHint(QPainter.Antialiasing, True)
			oldPen = painter.pen()
			painter.setPen(QPen(self.DROP_INDICATOR_COLOR, self.DROP_INDICATOR_WIDTH))
			rect = option.rect
			rect.setLeft(self.DROP_INDICATOR_WIDTH)
			rect.setRight(widget.width()-self.DROP_INDICATOR_WIDTH*2)
			if option.rect.height() == 0:
				painter.drawLine(rect.topLeft(), option.rect.topRight())
			else:
				painter.drawRect(rect)
			painter.setPen(oldPen)
			painter.restore()

	def generatedIconPixmap(self, iconMode, pixmap, option):
		return self.__parent.generatedIconPixmap(iconMode, pixmap, option)

	def hitTestComplexControl(self, control, option, position, widget = None):
		return self.__parent.hitTestComplexControl(control, option, position, widget)

	def itemPixmapRect(self, rectangle, alignment, pixmap):
		return self.__parent.itemPixmapRect(rectangle, alignment, pixmap)

	def itemTextRect(self, metrics, rectangle, alignment, enabled, text):
		return self.__parent.itemTextRect(metrics, rectangle, alignment, enabled, text)

	def pixelMetric(self, metric, option = None, widget = None):
		return self.__parent.pixelMetric(metric, option, widget)

	def polish(self, *args, **kwargs):
		return self.__parent.polish(*args, **kwargs)

	def styleHint(self, hint, option=None, widget=None, returnData=None):
		if hint == QStyle.SH_Slider_AbsoluteSetButtons:
			return Qt.LeftButton | Qt.MidButton | Qt.RightButton
		return self.__parent.styleHint(hint, option, widget, returnData)

	def subControlRect(self, control, option, subControl, widget = None):
		return self.__parent.subControlRect(control, option, subControl, widget)

	def subElementRect(self, element, option, widget = None):
		return self.__parent.subElementRect(element, option, widget)

	def unpolish(self, *args, **kwargs):
		return self.__parent.unpolish(*args, **kwargs)

	def sizeFromContents(self, ct, opt, contentsSize, widget = None):
		return self.__parent.sizeFromContents(ct, opt, contentsSize, widget)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
