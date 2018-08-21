from copy import deepcopy

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *

import maya.cmds as cmds
from maya.app.renderSetup.views.lightEditor.node import *
import maya.app.renderSetup.views.lightEditor.lightTypeManager as typeMgr
import maya.app.renderSetup.views.utils as viewsUtils
import maya.app.renderSetup.model.plug as plug
import math

"""
Base class for column delegates of various types.
"""
class ColumnDelegate(QStyledItemDelegate):

	# Constants
	DISABLED_BACKGROUND_IMAGE = viewsUtils.createPixmap((":/RS_disabled_tile.png"))
	DISABLED_HIGHLIGHT_IMAGE = viewsUtils.createPixmap((":/RS_disabled_tile_highlight.png"))
	BOTTOM_GAP_OFFSET = viewsUtils.dpiScale(2)

	def __init__(self):
		super(ColumnDelegate, self).__init__()

	def _isEditable(self, index):
		return ((index.flags() & Qt.ItemIsEditable) != 0)

	def _drawBackground(self, rect, painter, option, index):
		oldPen = painter.pen()
        
		painter.fillRect(rect, index.data(Qt.BackgroundRole))

		if index.data(ITEM_ROLE_ENABLED) and index.data(ITEM_ROLE_IS_LAYER_MEMBER):
			# Draw the highlight color
			if option.showDecorationSelected and option.state & QStyle.State_Selected:
				painter.fillRect(rect, option.palette.color(QPalette.Highlight))
		else:
			# Draw the highlight color
			if option.showDecorationSelected and option.state & QStyle.State_Selected:
				painter.drawTiledPixmap(rect, ColumnDelegate.DISABLED_HIGHLIGHT_IMAGE, QPoint(rect.left(), 0))
			# Otherwise draw our background color
			else:
				painter.drawTiledPixmap(rect, ColumnDelegate.DISABLED_BACKGROUND_IMAGE, QPoint(rect.left(), 0))

		painter.setPen(oldPen)

	def createEditor(self, parent, option, index):
		return None

	def paint(self, painter, option, index):
		if not index.isValid():
			return
		rect = deepcopy(option.rect)
		rect.setBottom(rect.bottom() - ColumnDelegate.BOTTOM_GAP_OFFSET)
		self._drawBackground(rect, painter, option, index)

"""
Delegate for name column.
"""
class NameDelegate(ColumnDelegate):

	# Constants
	ARROW_COLOR = QColor(189, 189, 189)
	LIGHT_ICON_SIZE = viewsUtils.dpiScale(20)
	LIGHT_ICON_OFFSET = viewsUtils.dpiScale(4)
	EXPANDED_ARROW = (viewsUtils.dpiScale(QPointF(9.0, 11.0)), viewsUtils.dpiScale(QPointF(19.0, 11.0)), viewsUtils.dpiScale(QPointF(14.0, 16.0)))
	COLLAPSED_ARROW = (viewsUtils.dpiScale(QPointF(12.0, 8.0)), viewsUtils.dpiScale(QPointF(17.0, 13.0)), viewsUtils.dpiScale(QPointF(12.0, 18.0)))

	def __init__(self, treeView):
		super(NameDelegate, self).__init__()
		self.treeView = treeView

		# Create all light icons
		self.lightTypeIcon = {}
		for lightType in typeMgr.lights():
			iconFile = typeMgr.getIcon(lightType)
			icon = QIcon(iconFile)
			self.lightTypeIcon[lightType] = icon

	def __del__(self):
		self.lightTypeIcon = {}

	def createEditor(self, parent, option, index):
		editor = QLineEdit(parent)
		editor.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
		return editor

	def updateEditorGeometry(self, editor, option, index):
		typeId = index.data(ITEM_ROLE_TYPE)
		indent = self.treeView.getIndent(index)
		rect = deepcopy(option.rect)
		if typeId == TYPE_ID_GROUP_ITEM:
			rect.setLeft(indent + viewsUtils.dpiScale(22.5))
		else:
			rect.setLeft(indent + viewsUtils.dpiScale(26.5))
		rect.setBottom(rect.bottom() - viewsUtils.dpiScale(4))
		editor.setGeometry(rect)

	def setEditorData (self, editor, index):
		editor.setText(index.model().data(index, Qt.DisplayRole))

	def setModelData(self, editor, model, index):
		oldValue = index.data()
		newValue = editor.text()
		if newValue != oldValue:
			model.setData(index, newValue)

	def paint(self, painter, option, index):
		if not index.isValid():
			return

		indent = self.treeView.getIndent(index)
		rect = deepcopy(option.rect)
		rect.setLeft(indent)
		rect.setBottom(rect.bottom() - ColumnDelegate.BOTTOM_GAP_OFFSET)

		self._drawBackground(rect, painter, option, index)

		typeId = index.data(ITEM_ROLE_TYPE)

		if typeId == TYPE_ID_GROUP_ITEM:
			# Draw the color bar
			rect2 = deepcopy(rect)
			rect2.setLeft(indent)
			rect2.setRight(indent + viewsUtils.dpiScale(6))
			painter.fillRect(rect2, index.data(ITEM_ROLE_COLOR_BAR))

			# Draw the expand arrow if the group has children
			if index.child(0, 0).isValid():
				painter.save()
				painter.translate(rect.left(), rect.top())
				arrow = None
				if self.treeView.isExpanded(index):
					arrow = self.EXPANDED_ARROW
				else:
					arrow = self.COLLAPSED_ARROW
				painter.setBrush(self.ARROW_COLOR)
				painter.setPen(Qt.NoPen)
				painter.drawPolygon(arrow)
				painter.restore()

		elif typeId == TYPE_ID_LIGHT_ITEM:
			# Draw the light icon
			lightType = index.data(ITEM_ROLE_LIGHT_TYPE)
			if lightType in self.lightTypeIcon:
				icon = self.lightTypeIcon[lightType]
				rect2 = deepcopy(rect)
				rect2.setLeft(rect.left() + self.LIGHT_ICON_OFFSET)
				rect2.setRight(rect.left() + self.LIGHT_ICON_OFFSET + self.LIGHT_ICON_SIZE-1)
				rect2.setTop(rect.top() + self.LIGHT_ICON_OFFSET)
				rect2.setBottom(rect.bottom() - self.LIGHT_ICON_OFFSET)
				pixmap = icon.pixmap(self.LIGHT_ICON_SIZE, self.LIGHT_ICON_SIZE)
				painter.drawPixmap(rect2, pixmap, pixmap.rect())

		# Draw the name text
		oldPen = painter.pen()
		painter.setPen(QPen(index.data(Qt.TextColorRole), 1))
		painter.setFont(index.data(Qt.FontRole))
		textRect = deepcopy(rect)
		textRect.setBottom(textRect.bottom() - viewsUtils.dpiScale(2))
		textRect.setLeft(textRect.left() + viewsUtils.dpiScale(28))
		textRect.setRight(textRect.right() - viewsUtils.dpiScale(11))
		painter.drawText(textRect, index.data(Qt.TextAlignmentRole), index.data(Qt.DisplayRole))
		painter.setPen(oldPen)

	def sizeHint(self, option, index):
		return QSize(viewsUtils.dpiScale(200), viewsUtils.dpiScale(14))

"""
Delegate for float field columns.
"""
class FloatFieldDelegate(ColumnDelegate):
	def __init__(self):
		super(FloatFieldDelegate, self).__init__()

	def _toStringTruncated(self, value):
		return ("%.6f" % value).rstrip("0").rstrip(".")

	def _toUI(self, value):
		return value

	def _toInternal(self, value):
		return value

	def createEditor(self, parent, option, index):
		value = index.data()
		if value == None: return None
		editor = QLineEdit(parent)
		editor.setAlignment(Qt.AlignHCenter|Qt.AlignVCenter)
		dv = QDoubleValidator()
		dv.setDecimals(6)
		dv.setNotation(QDoubleValidator.StandardNotation)
		editor.setValidator(dv)
		return editor

	def setEditorData(self, editor, index):
		value = self._toUI(index.data())
		valueStr = self._toStringTruncated(value)
		editor.setText(valueStr)

	def setModelData(self, editor, model, index):
		oldValue = self._toUI(index.data())
		oldValueStr = self._toStringTruncated(oldValue)
		newValueStr = editor.text()
		if newValueStr != oldValueStr:
			newValue = self._toInternal(float(newValueStr))
			model.setData(index, newValue)

	def paint(self, painter, option, index):
		if not index.isValid():
			return

		rect = deepcopy(option.rect)
		rect.setBottom(rect.bottom() - ColumnDelegate.BOTTOM_GAP_OFFSET)

		self._drawBackground(rect, painter, option, index)

		value = self._toUI(index.data())
		if value is None:
			return

		oldPen = painter.pen()
		painter.setPen(QPen(index.data(Qt.TextColorRole), 1))
		painter.setFont(index.data(Qt.FontRole))
		truncated = ("%.3f" % value).rstrip("0").rstrip(".")
		painter.drawText(rect, index.data(Qt.TextAlignmentRole), truncated)
		painter.setPen(oldPen)

"""
Delegate for angle field columns. A float delegate with angle conversions.
"""
class AngleFieldDelegate(FloatFieldDelegate):
	def __init__(self):
		super(AngleFieldDelegate, self).__init__()

	def _toUI(self, value):
		return math.degrees(value)

	def _toInternal(self, value):
		return math.radians(value)

"""
Delegate for integer field columns.
"""
class IntFieldDelegate(ColumnDelegate):
	def __init__(self):
		super(IntFieldDelegate, self).__init__()

	def createEditor(self, parent, option, index):
		value = index.data()
		if value == None: return None
		editor = QLineEdit(parent)
		editor.setAlignment(Qt.AlignHCenter|Qt.AlignVCenter)
		editor.setValidator(QIntValidator())
		return editor

	def setEditorData(self, editor, index):
		cont = index.model().data(index, Qt.DisplayRole)
		editor.setText(str(cont))

	def setModelData(self, editor, model, index):
		oldValue = index.data()
		newValue = int(editor.text())
		if newValue != oldValue:
			model.setData(index, newValue)

	def paint(self, painter, option, index):
		if not index.isValid():
			return

		rect = deepcopy(option.rect)
		rect.setBottom(rect.bottom() - ColumnDelegate.BOTTOM_GAP_OFFSET)

		self._drawBackground(rect, painter, option, index)

		value = index.data()
		if value is None:
			return

		oldPen = painter.pen()
		painter.setPen(QPen(index.data(Qt.TextColorRole), 1))
		painter.setFont(index.data(Qt.FontRole))
		painter.drawText(rect, index.data(Qt.TextAlignmentRole), str(value))
		painter.setPen(oldPen)

"""
Delegate for check box columns.
"""
class CheckBoxDelegate(ColumnDelegate):
	def __init__(self):
		super(CheckBoxDelegate, self).__init__()

	def createEditor(self, parent, option, index):
		return None

	def editorEvent(self, event, model, option, index):
		if event.type() == QEvent.MouseButtonPress and (QApplication.mouseButtons() == Qt.LeftButton):
			if self._isEditable(index):
				model.setData(index, not model.data(index, Qt.DisplayRole))
			event.accept()
			return True
		elif event.type() == QEvent.MouseButtonRelease and (QApplication.mouseButtons() == Qt.NoButton):
			event.accept()
			return True

		return False

	def paint(self, painter, option, index):
		if not index.isValid():
			return

		rect = deepcopy(option.rect)
		rect.setBottom(rect.bottom() - self.BOTTOM_GAP_OFFSET)

		self._drawBackground(rect, painter, option, index)

		value = index.data()
		if value!=None:
			newopt = QStyleOptionButton()
			checkboxRect = QApplication.style().subElementRect(QStyle.SE_CheckBoxIndicator, newopt)
			newopt.rect = deepcopy(rect)
			newopt.rect.setLeft(rect.left() + rect.width()/2 - checkboxRect.width()/2)
			newopt.palette = option.palette
			newopt.state |= QStyle.State_On if value else QStyle.State_Off
			QApplication.style().drawControl(QStyle.CE_CheckBox, newopt, painter)

"""
Delegate for color picker columns.
"""
class ColorPickerDelegate(ColumnDelegate):
	def __init__(self):
		super(ColorPickerDelegate, self).__init__()

	def createEditor(self, parent, option, index):
		return None

	def paint(self, painter, option, index):
		if not index.isValid():
			return

		rect = deepcopy(option.rect)
		rect.setBottom(rect.bottom() - ColumnDelegate.BOTTOM_GAP_OFFSET)

		self._drawBackground(rect, painter, option, index)

		color = index.data(Qt.DisplayRole)
		if color is None:
			return

		w = rect.width()
		ad = (w - viewsUtils.dpiScale(50))/2
		if ad<=0:
			ad=0

		# Transform color to display space and clamp to [0,1] range
		# to make sure QT will draw it correctly
		displayColor = cmds.colorManagementConvert(toDisplaySpace = color)
		displayColor = [max(min(v, 1.0), 0.0) for v in displayColor]

		# Draw the color swatch
		displayColorQ = QColor.fromRgbF(*displayColor)
		painter.fillRect(rect.adjusted(ad, viewsUtils.dpiScale(5), -ad, viewsUtils.dpiScale(-5)), displayColorQ)

	def editorEvent(self, event, model, option, index):
		if event.type() == QEvent.MouseButtonPress:
			value = index.data()
			if value == None: return False

			if self._isEditable(index):
				mousePos = QCursor.pos() # We did not get a mouse event so get mouse like this
				screenSize = QApplication.desktop().availableGeometry(mousePos)
				maxX = screenSize.left() + screenSize.width() - viewsUtils.dpiScale(430)
				maxY = screenSize.top() + screenSize.height() - viewsUtils.dpiScale(270)
				minX = screenSize.left()
				minY = screenSize.top()

				pos = QPoint(mousePos.x() - viewsUtils.dpiScale(200), mousePos.y() - viewsUtils.dpiScale(100))
				if pos.x() > maxX:
					pos.setX(maxX)
				elif pos.x() < minX:
					pos.setX(minX)

				if pos.y() > maxY:
					pos.setY(maxY)
				elif pos.y() < minY:
					pos.setY(minY)

				cmds.colorEditor(mini=True, rgbValue=index.data(Qt.DisplayRole), position = (pos.x(), pos.y()))
				if cmds.colorEditor(q=True, result=True):
					newValue = cmds.colorEditor(q=True, rgbValue=True)
					oldValue = index.data()
					if newValue != oldValue:
						model.setData(index, newValue)

			event.accept()
			return True

		elif event.type() == QEvent.MouseButtonRelease:
			event.accept()
			return True

		return False

"""
Compound delegate handling all attributes.
Matching the attribute type with one of the delegates above.
"""
class AttributeDelegate(QStyledItemDelegate):

	def __init__(self, treeView):
		super(AttributeDelegate, self).__init__()

		self.defaultDelegate = ColumnDelegate()
		self.nameDelegate = NameDelegate(treeView)

		self.delegateForType = {
			plug.Plug.kInvalid  : self.defaultDelegate,
			plug.Plug.kFloat    : FloatFieldDelegate(),
			plug.Plug.kDouble   : FloatFieldDelegate(),
			plug.Plug.kInt      : IntFieldDelegate(),
			plug.Plug.kBool     : CheckBoxDelegate(),
			plug.Plug.kColor    : ColorPickerDelegate(),
			plug.Plug.kEnum     : IntFieldDelegate(),
			plug.Plug.kTime     : FloatFieldDelegate(),
			plug.Plug.kAngle    : AngleFieldDelegate(),
			plug.Plug.kDistance : FloatFieldDelegate()
		}

	def _delegate(self, index):
		if index.column() == 0:
			return self.nameDelegate
		if index.data(ITEM_ROLE_ATTR_HIDDEN):
			return self.defaultDelegate
		attrType = index.data(ITEM_ROLE_ATTR_TYPE)
		return self.delegateForType[attrType]

	def createEditor(self, parent, option, index):
		return self._delegate(index).createEditor(parent, option, index)

	def setEditorData (self, editor, index):
		return self._delegate(index).setEditorData(editor, index)

	def updateEditorGeometry(self, editor, option, index):    
		return self._delegate(index).updateEditorGeometry(editor, option, index)

	def setModelData(self, editor, model, index):
		return self._delegate(index).setModelData(editor, model, index)

	def paint(self, painter, option, index):
		return self._delegate(index).paint(painter, option, index)

	def sizeHint(self, option, index):
		return self._delegate(index).sizeHint(option, index)

	def editorEvent(self,event, model, option, index):
		return self._delegate(index).editorEvent(event, model, option, index)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
