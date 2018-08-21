import maya
maya.utils.loadStringResourcesForModule(__name__)

from maya.api import OpenMaya as om
from maya.app.renderSetup.views.lightEditor.node import *
import maya.app.renderSetup.views.lightEditor.utils as utils
from maya import cmds as cmds
import maya.app.renderSetup.model.undo as undo

from PySide2.QtCore import Qt

ENABLE_LIGHT_EDITOR_GROUP_CMD = maya.stringTable['y_group.kEnableLightEditorGroup' ]

class GroupAttributes(NodeAttributes):
	def __init__(self):
		NodeAttributes.__init__(self)

class Group(Node):
	"""
	This class wraps a group node (objectSet) in Maya.
	"""

	def __init__(self, model, mayaObj, attributes):
		super(Group, self).__init__(model, mayaObj, attributes)
		self.children = []

		# Create dynamic attributes needed to store node state
		utils.createDynamicAttribute(self.mayaName(), "isolate", "bool", False)
		utils.createDynamicAttribute(self.mayaName(), "wasEnabled", "bool", True)
		utils.createDynamicAttribute(self.mayaName(), "childIndex", "long", -1)
		utils.createDynamicAttribute(self.mayaName(), "lightGroup", "bool", True)
		utils.createDynamicAttribute(self.mayaName(), "visibility", "bool", True)

		# Setup all needed callbacks

		def _nodePreRemovalCB(obj, clientData):
			# Don't enable MayaScope for removal callback
			# doDelete must be callable from both LightScope and MayaScope in
			# order for all possible delete cases to work.
			# Instead we have made doDelete safe to call multiple times.
			if self.model.isResetting(): return
			if obj == self.getShape():
				# First, delete all children
				# This will delete the Maya DG nodes and call the 
				# pre-removal callbacks for each existing child
				nodes = [c.mayaName() for c in self.children if c.hasMayaResource()]
				if len(nodes)>0:
					cmds.delete(nodes)
				# Second, cleanup internal state for this node
				self.doDelete()

		self.nodePreRemovalCallbackId = om.MNodeMessage.addNodePreRemovalCallback(mayaObj, _nodePreRemovalCB)

	def __del__(self):
		self.dispose()

	def dispose(self):
		if self.disposed: return

		if self.nodePreRemovalCallbackId:
			om.MMessage.removeCallback(self.nodePreRemovalCallbackId)
			self.nodePreRemovalCallbackId = 0

		for i in range(len(self.children)):
			self.children[i].dispose()
		self.children = []

		super(Group, self).dispose()

	def mayaName(self):
		return om.MFnDependencyNode(self.mayaHandle.object()).name()

	def typeId(self):
		return TYPE_ID_GROUP_ITEM

	def data(self, role, column):
		if role == Qt.BackgroundRole:
			return GROUP_COLOR
		elif role == ITEM_ROLE_COLOR_BAR:
			return GROUP_BAR_COLOR
		return super(Group, self).data(role, column)

	def flags(self, index):
		col = index.column()
		flags = 0
		flags |= Qt.ItemIsDropEnabled
		flags |= Qt.ItemIsEnabled
		flags |= Qt.ItemIsSelectable
		if col == 0:
			# Column 0 is the item name
			flags |= Qt.ItemIsDragEnabled
			if self.hasMutableName:
				flags |= Qt.ItemIsEditable
		else:
			flags |= Qt.ItemIsEditable
		return flags

	def childCount(self):
		return len(self.children)

	def child(self, i):
		return self.children[i]

	def insertChild(self, child, row = -1):
		# Update Maya state
		if self.hasMayaResource() and child.hasMayaResource():
			cmds.sets(child.mayaName(), include=self.mayaName())

		# Update internal state
		if not self.hasChild(child):
			if row < 0:
				row = len(self.children) # Insert last

			myIndex = self.model.indexFromNode(self)
			self.model.beginInsertRows(myIndex, row, row)
			self.children.insert(row, child)
			child.setParent(self)
			child._setChildIndex(row)
			self.model.endInsertRows()

			# Update all child indices for this parent
			for i in range(len(self.children)):
				self.children[i]._setChildIndex(i)

			# Sync any child state that should affect the parent
			self.syncWithChildren()

	def removeChild(self, child):
		# Update Maya state
		if self.hasMayaResource() and child.hasMayaResource():
			cmds.sets(child.mayaName(), remove=self.mayaName())

		# Update internal state
		if self.hasChild(child):
			row = self.children.index(child)
			myIndex = self.model.indexFromNode(self)
			self.model.beginRemoveRows(myIndex, row, row)
			child.setParent(None)
			child._setChildIndex(-1)
			del self.children[row]
			self.model.endRemoveRows()

			# Update all child indices for this parent
			for i in range(len(self.children)):
				self.children[i]._setChildIndex(i)

			# Sync any child state that should affect the parent
			self.syncWithChildren()

	def hasChild(self, child):
		for i in range(len(self.children)):
			if self.children[i] is child:
				return True
		return False

	def syncWithChildren(self):
		if self.childCount() > 0:
			# Sync enable state
			numEnabled = 0
			for child in self.children:
				numEnabled += 1 if child.isEnabled() else 0
			self._setPrivateValue("visibility", (numEnabled > 0))
			self.emitDataChanged(-1)

		if self.parent():
			self.parent().syncWithChildren()

	def doDelete(self):
		if self.disposed:
			return

		# Do delete of all children
		# This will remove the child element from the list, 
		# so pop the last child until list is empty
		last = len(self.children) - 1
		while last >= 0:
			if not self.children[last].disposed:
				self.children[last].doDelete()
			else:
				self.children.pop(last)    
			last = len(self.children) - 1

		# Remove ourself from parent
		parent = self.parent()
		if parent:
			parent.removeChild(self)

		# Remove ourself from the model
		tmp = self.model.groups.pop(self.uuid(), None)

		# Call base cLass doDelete
		super(Group, self).doDelete()

	@undo.chunk(ENABLE_LIGHT_EDITOR_GROUP_CMD)
	def enable(self, value):
		for child in self.children:
			child.enable(value)

		attr = self.attributes.findAttributeByLabel("Enable")
		self._setAttributePlugValue(attr, value)

		# Enable affects the whole item row, so emit data changed for all columns
		self.emitDataChanged(-1)

		# Enable changes can affect the parent
		if self.parent():
			self.parent().syncWithChildren()

	def isolate(self, value):
		for child in self.children:
			child.isolate(value)

		self._setPrivateValue("isolate", value)
# ===========================================================================
# Copyright 2016 Autodesk, Inc. All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license
# agreement provided at the time of installation or download, or which
# otherwise accompanies this software in either electronic or hard copy form.
# ===========================================================================
