from maya.api import OpenMaya as om
from maya import cmds as cmds

import maya.app.renderSetup.views.utils as viewsUtils
import maya.app.renderSetup.views.lightEditor.enterScope as enterScope
import maya.app.renderSetup.common.utils as commonUtils
import maya.app.renderSetup.model.plug as plugModule

from PySide2.QtCore import Qt, QSize
from PySide2.QtGui import QColor, QGuiApplication
from PySide2.QtWidgets import QApplication

# Type id's for items
TYPE_ID_UNDEFINED   = 0
TYPE_ID_LIGHT_ITEM  = 1
TYPE_ID_GROUP_ITEM  = 2

# All needed roles
ITEM_ROLE_TYPE       = Qt.UserRole + 0
ITEM_ROLE_ENABLED    = Qt.UserRole + 1
ITEM_ROLE_ISOLATED   = Qt.UserRole + 2
ITEM_ROLE_LIGHT_TYPE = Qt.UserRole + 3
ITEM_ROLE_COLOR_BAR  = Qt.UserRole + 4
ITEM_ROLE_ATTR_TYPE  = Qt.UserRole + 5
ITEM_ROLE_ATTR_HIDDEN = Qt.UserRole + 6
ITEM_ROLE_IS_LAYER_MEMBER = Qt.UserRole + 7

GROUP_COLOR     = QColor(76, 76, 76)
LIGHT_COLOR     = QColor(59, 59, 59)
GROUP_BAR_COLOR = QColor(120, 120, 120)
LIGHT_BAR_COLOR = QColor(179, 177, 71)

LIGHT_TEXT_COLOR = QColor(255,255,255)
LIGHT_TEXT_COLOR_OVERRIDEN_BY_US = QColor(229, 105, 41)
LIGHT_TEXT_COLOR_LOCKED = QColor(92,104,116)
LIGHT_TEXT_COLOR_ANIMATED = QColor(255,0,0)

class Attribute():
	def __init__(self, label, name, setter=None, getter=None):
		self.label  = label
		self.name   = name
		self.setter = setter
		self.getter = getter
		self.index  = -1

class NodeAttributes():
	def __init__(self):
		self.attributes = []
		self.attributesByName  = {}
		self.attributesByLabel = {}

		# Add attribute for setting/getting name

		def _nameSetter(node, attrName, value):
			cmds.rename(node.mayaName(), value)

		def _nameGetter(node, attrName):
			dn = om.MFnDependencyNode(node.mayaHandle.object())
			return dn.name()

		self.addAttribute( Attribute("Name", "name", _nameSetter, _nameGetter) )

		# Add attribute for enable/isolate

		def _enableSetter(node, attrName, value):
			node.enable(value)

		def _enableGetter(node, attrName):
			return node.isEnabled()

		def _isolateSetter(node, attrName, value):
			node.isolate(value)

		def _isolateGetter(node, attrName):
			return node.isIsolated()

		self.addAttribute( Attribute("Enable", "visibility", _enableSetter, _enableGetter) )
		self.addAttribute( Attribute("Isolate", "isolate", _isolateSetter, _isolateGetter) )

	def __del__(self):
		del self.attributes
		del self.attributesByName
		del self.attributesByLabel

	def count(self):
		return len(self.attributes)

	def addAttribute(self, attr):
		attr.index = self.count()
		self.attributes.append(attr)
		self.attributesByName[attr.name]   = attr
		self.attributesByLabel[attr.label] = attr

	def findAttributeByIndex(self, index):
		if index < self.count():
			return self.attributes[index]
		else:
			return None

	def findAttributeByName(self, name):
		if name in self.attributesByName:
			return self.attributesByName[name]
		else:
			return None

	def findAttributeByLabel(self, label):
		if label in self.attributesByLabel:
			return self.attributesByLabel[label]
		else:
			return None


class Node(object):
	"""
	This class wraps a DAG node in Maya.
	"""

	ITEM_ROW_HEIGHT = viewsUtils.dpiScale(30)

	def __init__(self, model, obj, attributes):
		super(Node, self).__init__()
		self.disposed = False
		self.model = model
		self.mayaHandle = om.MObjectHandle(obj)
		self.attributes = attributes
		self.parentNode = None
		self.hasMutableName = False

		# Set callback for name changes
		def _nameChangedCB(obj, oldName, clientData):
			if len(oldName)>0:
				self.nameChanged(oldName)

		self.nameChangedCallbackId = om.MNodeMessage.addNameChangedCallback(self.mayaHandle.object(), _nameChangedCB)

	def __del__(self):
		self.dispose()

	@staticmethod
	def getUuid(obj):
		# The UUID's on the Maya nodes are not unique for referenced objects.
		# So instead we use the internal hash code available on the MObjectHandle
		# to identify our nodes
		h = om.MObjectHandle(obj)
		return h.hashCode()

	def dispose(self):
		if self.disposed: return
		self.disposed = True

		if self.nameChangedCallbackId:
			om.MMessage.removeCallback(self.nameChangedCallbackId)
			self.nameChangedCallbackId = 0

		del self.mayaHandle
		self.mayaHandle = None
		self.attributes = None

	def typeId(self):
		return TYPE_ID_UNDEFINED

	def uuid(self):
		# The UUID's on the Maya nodes are not unique for referenced objects.
		# So instead we use the internal hash code available on the MObjectHandle
		# to identify our nodes
		return self.mayaHandle.hashCode()

	def setName(self, name):
		# Set name using the name attribute
		self.setAttributeByLabel("Name", name)

	def getName(self):
		# Get name using the name attribute
		return self.getAttributeByLabel("Name")

	def nameChanged(self, oldName):
		self.emitAttributeChanged("name")

	def getShape(self):
		return self.mayaHandle.object()

	def getShapeName(self):
		dn = om.MFnDependencyNode(self.mayaHandle.object())
		return dn.name()

	def childCount(self):
		return 0

	def child(self, i):
		return None

	def insertChild(self, child, i = -1):
		pass

	def removeChild(self, child):
		pass

	def hasChild(self, child):
		return False

	def parent(self):
		return self.parentNode

	def setParent(self, parent):
		self.parentNode = parent

	def syncWithChildren(self):
		pass

	def mayaName(self):
		pass

	def hasMayaResource(self):
		return self.mayaHandle.isValid()

	def nodesToDelete(self):
		pass

	def doDelete(self):
		self.dispose()

	def data(self, role, column):
		if role == Qt.TextColorRole:
			return QGuiApplication.palette().text().color()
		elif role == Qt.FontRole:
			return QApplication.font()
		elif role == Qt.TextAlignmentRole:
			if column==0:
				return Qt.AlignLeft | Qt.AlignVCenter
			else:
				return Qt.AlignCenter | Qt.AlignVCenter
		elif role == Qt.SizeHintRole:
			return QSize(0, self.ITEM_ROW_HEIGHT)
		elif role == ITEM_ROLE_TYPE:
			return self.typeId()
		elif role == Qt.EditRole:
			return self.getAttributeByIndex(column)
		elif role == Qt.DisplayRole:
			return self.getAttributeByIndex(column)
		elif role == ITEM_ROLE_ENABLED:
			return self.getAttributeByLabel("Enable")
		elif role == ITEM_ROLE_ISOLATED:
			return self.getAttributeByLabel("Isolate")
		elif role == ITEM_ROLE_ATTR_TYPE:
			return self.attributeType(column)
		elif role == ITEM_ROLE_ATTR_HIDDEN:
			return self.attributeHidden(column)
		elif role == ITEM_ROLE_IS_LAYER_MEMBER:
			return self._isMemberOfVisibleLayer()
		return None

	def setData(self, value, role, column):
		""" Sets the role data for the item. """
		attr = self.attribute(column)
		if not attr:
			return
		if role == Qt.EditRole:
			self.setAttributeByIndex(column, value)
		elif role == ITEM_ROLE_ENABLED:
			self.setAttributeByLabel("Enable", value)
		elif role == ITEM_ROLE_ISOLATED:
			self.setAttributeByLabel("Isolate", value)

	def emitDataChanged(self, column):
		myIndex = self.model.indexFromNode(self)
		row = myIndex.row()
		if column < 0:
			columnCount = self.attributes.count()
			idx1 = self.model.index(row, 0)
			idx2 = self.model.index(row, columnCount)
			self.model.emitDataChanged(idx1, idx2)
		else:
			idx = self.model.index(row, column)
			self.model.emitDataChanged(idx, idx)

	def emitAttributeChanged(self, attrName):
		if attrName == "visibility":
			# For visibility we need to update the whole row
			self.emitDataChanged(-1)
		else:
			# Find the index for this attribute and update it
			attr = self.attributes.findAttributeByName(attrName)
			if attr:
				self.emitDataChanged(attr.index)

	def attribute(self, column):
		return self.attributes.findAttributeByIndex(column)

	def attributeType(self, column):
		attr = self.attributes.findAttributeByIndex(column)
		if not attr:
			return plugModule.Plug.kInvalid
		plug = commonUtils.findPlug(self.getShape(), attr.name)
		return plugModule.Plug(plug).type if plug else plugModule.Plug.kInvalid

	def attributeHidden(self, column):
		attr = self.attributes.findAttributeByIndex(column)
		if attr:
			plg = plugModule.Plug(self.getShape(), attr.name)
			if plg.isValid:
				return plg.attribute().hidden
		return True

	def getAttributeByLabel(self, attrLabel):
		""" Gets the value of a given attribute. Returns None if the attribute doesn't exists. """
		attr = self.attributes.findAttributeByLabel(attrLabel)
		if not attr: return None
		return self._getAttribute(attr)

	def setAttributeByLabel(self, attrLabel, value):
		""" Sets the value of a given attribute. Does nothing if the attribute doesn't exists. """
		attr = self.attributes.findAttributeByLabel(attrLabel)
		if not attr: return None
		self._setAttribute(attr, value)

	def getAttributeByName(self, attrName):
		""" Gets the value of a given attribute. Returns None if the attribute doesn't exists. """
		attr = self.attributes.findAttributeByName(attrName)
		if not attr: return None
		return self._getAttribute(attr)

	def setAttributeByName(self, attrName, value):
		""" Sets the value of a given attribute. Does nothing if the attribute doesn't exists. """
		attr = self.attributes.findAttributeByName(attrName)
		if not attr: return None
		self._setAttribute(attr, value)

	def getAttributeByIndex(self, index):
		""" Gets the value of a given attribute. Returns None if the attribute doesn't exists. """
		attr = self.attributes.findAttributeByIndex(index)
		if not attr: return None
		return self._getAttribute(attr)

	def setAttributeByIndex(self, index, value):
		""" Sets the value of a given attribute. Does nothing if the attribute doesn't exists. """
		attr = self.attributes.findAttributeByIndex(index)
		if not attr: return None
		self._setAttribute(attr, value)

	def enable(self, value):
		pass

	def isEnabled(self):
		attr = self.attributes.findAttributeByLabel("Enable")
		return self._getAttributePlugValue(attr)

	def isolate(self, value):
		pass

	def isIsolated(self):
		attr = self.attributes.findAttributeByLabel("Isolate")
		return self._getAttributePlugValue(attr)

	def _getAttribute(self, attr):
		if attr.getter:
			return attr.getter(self, attr.name)
		else:
			return self._getAttributePlugValue(attr)

	def _setAttribute(self, attr, value):
		# Ignore the new value if it's not different from old
		oldValue = self._getAttribute(attr)
		if value == oldValue:
			return

		if attr.setter:
			attr.setter(self, attr.name, value)
		else:
			self._setAttributePlugValue(attr, value)
		
		self.emitDataChanged(attr.index)

	def _getPlugValue(self, plug):
		""" Get the value of a plug. """
		plugHandle = plugModule.Plug(plug)
		return plugHandle.value

	def _setPlugValue(self, plug, value):
		""" Set the value of a plug. """
		plugHandle = plugModule.Plug(plug)
		plugHandle.value = value

	def _getAttributePlugValue(self, attr):
		""" Get the value of an attribute. Considering overrides set on the attribute (if any). """
		plug = self._findPlug(attr)
		return self._getPlugValue(plug) if plug else None

	def _setAttributePlugValue(self, attr, value):
		""" Set the value of an attribute. Creating override on the attribute if needed. """
		with enterScope.EnterLightScope(self.model) as scope:
			if scope.active:
				plug = self._findPlug(attr, writeMode=True)
				if plug:
					self._setPlugValue(plug, value)

	def _findPlug(self, attr, writeMode=False):
		""" Find the plug matching the attribute name. 
		This method is overridden in derived classes. Default implementation returns 
		the ordinary attribute plug and doesn't handle overrides. """
		shapeNode = self.getShape()
		if not shapeNode:
			return None

		fnShapeNode = om.MFnDependencyNode(shapeNode)
		plug = None
		try:
			plug = fnShapeNode.findPlug(attr.name, False)
			# MAYA-66632: Could be improved by also checking if the 
			# plug type matches the given attribute type
		except:
			return None

		return plug

	def _getPrivateValue(self, attrName):
		""" Utility method to get the value of a private attribute. 
		An attribute that is only used internally and cannot have overrides on it. """
		plug = commonUtils.findPlug(self.getShape(), attrName)
		return self._getPlugValue(plug) if plug else None

	def _setPrivateValue(self, attrName, value):
		""" Utility method to set the value of a private attribute. 
		An attribute that is only used internally and cannot have overrides on it. """
		plug = commonUtils.findPlug(self.getShape(), attrName)
		if plug:
			self._setPlugValue(plug, value)

	def index(self):
		return self.model.indexFromNode(self)

	def _setChildIndex(self, value):
		plug = commonUtils.findPlug(self.getShape(), "childIndex")
		if plug:
			plug.setInt(value)

	def _getChildIndex(self):
		plug = commonUtils.findPlug(self.getShape(), "childIndex")
		return plug.asInt() if plug else None

	def _isMemberOfVisibleLayer(self):
		return True
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
